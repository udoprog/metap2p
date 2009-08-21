import hashlib
import os
import uuid

from metap2p.trdparty import bencode

class MetaError(Exception):
  pass

class MetaFile:
  PIECE_LENGTH=2**18
  SEP='/'
  EXT='cns'
  
  def __init__(self, dir=None, **kw):
    if dir and not os.path.isdir(dir):
      raise MetaError("MetaFile: cannot find base directory")
    
    self.id = str(uuid.uuid1().hex);
    self.dir = dir
    self.files = dict();
    self.dirs = list();
    self.pieces = "";
    self.real_paths = dict();
    self.piece_length = kw.get('piece_length', self.PIECE_LENGTH)
    self.ext = kw.get('ext', self.EXT)
    self.sep = kw.get('sep', self.SEP)
    self.need = None
    
    name = kw.get('name', None)

    from_meta = kw.get('from_meta', None)
    from_path = kw.get('from_path', None)
    
    if name:
      self.name = name
    elif self.dir:
      self.name = os.path.basename(self.dir)
    else:
      self.name = self.id
    
    if from_meta:
      self._loads(from_meta._dumps())
    elif from_path:
      f = open(from_path, 'r')
      self.loads(f.read())
      f.close();
    elif kw.get('digest', True):
      self._digest();

  def __open_f(self, fn, fp, mode):
    return open(fp, mode)

  def _walk(self, dir):
    newpaths = list();
    
    for p in os.listdir(self.dir):
      pp = os.path.join(self.dir, p)
      
      if (os.path.isfile(pp) or os.path.isdir(pp)) and not os.path.islink(pp):
        newpaths.insert(0, (pp, p))
    
    while True:
      if len(newpaths) == 0:
        break
      
      fp, fn = newpaths.pop();

      if not os.path.isfile(fp) and not os.path.isdir(fp) or os.path.islink(fp):
        continue
      
      yield (os.path.isdir(fp), fp, fn)
      
      if os.path.isdir(fp):
        for p in os.listdir(fp):
          pp = os.path.join(fp, p)
          newpaths.insert(0, (pp, self.sep.join((fn, p))))
  
  def _digest(self):
    dirs = list();
    files = dict();
    real_paths = dict();
    
    for is_dir, fp, fn in self._walk(self.dir):
      if is_dir:
        dirs.append(fn)
      else:
        real_paths[fn] = fp
    
    self.dirs = dirs
    self.files = files
    self.real_paths = real_paths
    
    self._digest_files();

  def _load_real_paths(self):
    fh = dict();

    if self.dir:
      for fn in self.files:
        fh[fn] = os.path.join(self.dir, fn.replace(self.sep, os.sep))
    else:
      for fn in self.files:
        fh[fn] = ""
    
    return fh
  
  def _digest_files(self):
    pieces = list()
    
    for fn, fp in self.real_paths.items():
      file_size = 0
      
      f = self.__open_f(fn, fp, 'r')
      
      m_all = hashlib.new('sha1')
      
      hash_offset = len(pieces)
      
      while True:
        s = f.read(self.piece_length)

        if len(s) == 0 or not s:
          break
        
        file_size += len(s)
        
        m_all.update(s)
        
        m = hashlib.new('sha1', s)
        pieces.append(m.digest())
        del m
      
      hash_length = len(pieces) - hash_offset
      self.files[fn] = (hash_offset, hash_length, file_size, m_all.digest())
      #pieces[fn] = fh
    
    f.close();
    self.pieces = ''.join(pieces)
  
  def _check_files(self):
    for fn in self.files:
      yield((fn, list(self._check_file(fn))))
  
  def _check_file(self, fn):
    ff = self.__find(fn)

    if not ff:
      raise MetaError('File does not exist - %s'%(fn))

    hash_offset, hash_length, size, digest = ff
    
    m_all = hashlib.new('sha1')
    
    f = self.__open_f(fn, self.__find_path(fn), 'r')

    for cc in range(hash_length):
      s = f.read(self.piece_length)
      
      if not s:
        raise MetaError('File size mismatch')
      
      m_all.update(s)
      
      yield self._validate_chunk(fn, ff, cc, s)
    
    if digest != m_all.digest():
      pass
    
    del m_all
    f.close();
  
  def _validate_chunk(self, fn, ff, cc, s):
    m = hashlib.new('sha1', s)
    
    hash_offset, hash_length, size, digest = ff
    
    chunk_digest = self.__find_hash(hash_offset, cc)
    
    f_l = min((size - self.piece_length * cc), self.piece_length)
    
    if len(s) != f_l:
      raise MetaError('File invalid, part %d length invalid'%(cc))
    
    if chunk_digest != m.digest():
      return((cc, False))
    else:
      return((cc, True))
  
  def _dumps(self):
    base = dict();
    base['id'] = self.id
    base['dirs'] = self.dirs
    base['files'] = self.files
    base['pieces'] = self.pieces
    base['piece length'] = self.piece_length
    base['name'] = self.name
    
    return base

  def dumps(self):
    return bencode.bencode(self._dumps())
  
  def _loads(self, base):
    self.id =     base['id']
    self.name =   base['name']
    self.dirs =   base['dirs']
    self.files =  base['files']
    self.pieces = base['pieces']
    
    self.piece_length = base.get('piece length', self.PIECE_LENGTH)
    self.real_paths = self._load_real_paths()

  def __find(self, fn):
    return self.files.get(fn, None)
  
  def __find_path(self, fn):
    return self.real_paths.get(fn, None)
    #for fp, fn in self.real_paths:
    #  if fn == fn:
    #    return (fp, fn)
    #
    #return None
  
  def __find_hash(self, offs, cc):
    #return self.pieces[offs + cc]
    sp = 20 * (offs + cc)
    return self.pieces[sp:sp + 20];
  
  def loads(self, base_s):
    return self._loads(bencode.bdecode(base_s))
  
  def all_valid(self):
    return all(map(lambda fn: all(map(lambda fp: fp[1],self.validate(fn))), self.files))
  
  def validate(self, fn):
    for pp in self._check_file(fn):
      yield pp
    
    return
  
  def filename(self):
    return "%s.%s"%(self.name, self.ext)
  
  def read(self, fn, cc):
    ff = self.__find(fn)

    if not ff:
      return ((-1, False), "")

    hash_offset, hash_length, size, digest = ff
    
    fp = self.__find_path(fn)
    
    if not (cc >= 0 and cc < hash_length):
      return ((-1, False), "")
    
    f = self.__open_f(fn, fp, 'r')
    f.seek(self.piece_length * cc)
    s = f.read(self.piece_length)
    f.close();
    
    return (self._validate_chunk(fn, ff, cc, s), s)
  
  def write(self, fn, cc, s):
    ff = self.__find(fn)

    if not ff:
      return ((-1, False), "")

    hash_offset, hash_length, size, digest = ff
    
    fp = self.__find_path(fn)
    
    if not (cc >= 0 and cc < hash_length):
      return ((-1, False), "")
    
    chunk_v = self._validate_chunk(fn, ff, cc, s)
    
    if not chunk_v[1]:
      return chunk_v
    
    f = self.__open_f(fn, fp, 'r+')
    f.seek(self.piece_length * cc)
    f.write(s)
    f.close();
    
    fp = self.__find_path(fn)

    return chunk_v

  def create_directories(self):
    for d in self.dirs:
      a_dir = os.path.join(self.dir, d.replace(self.sep, os.sep))
      
      if not os.path.isdir(a_dir):
        print "C", a_dir
        os.mkdir(a_dir)

  def create_skeletons(self, fn=None):
    def single(fn):
      hash_offset, hash_length, size, digest = self.__find(fn)
      fp = self.__find_path(fn)
      
      if not os.path.isfile(fp):
        print "C", fp
        
        f = self.__open_f(fn, fp, 'w')
        f.write("\0" * size)
        f.close();
    
    if not fn:
      for fn in self.files:
        single(fn)
    else:
      single(fn)
  
  def generate_needs(self):
    """
    Generate a list of tuples containing invalid (or missing) file parts.
    Should be run when all skeleton files are present, otherwise i don't know what will happen.
    """
    needs = list();
    
    for fn in self.files:
      # create skeletons
      self.create_skeletons(fn)
      
      # filter valid chunks and map just tuples with (fn, cc)
      for ff in self.validate(fn):
        if ff[1]:
          continue
        
        yield (fn, ff[0])

  def __valid_base(self, base):
    if not 'id' in base:
      raise MetaError("base: missing key 'id'")
    
    if not 'dirs' in base:
      raise MetaError("base: missing key 'dirs'")
    
    if not type(base['dirs']) == list:
      raise MetaError("base: dirs entry not a list")
    
    if not 'files' in base:
      raise MetaError("base: missing key 'files'")
    
    if not type(base['dirs']) == list:
      raise MetaError("base: 'dirs' entry not a list")
    
    base['pieces'] = self.pieces
    base['piece length'] = self.piece_length
    base['name'] = self.name


if __name__ == '__main__':
  import sys
  sys.path.append('.')
  
  m = MetaFile('./testa')

  if not os.path.isfile('testa.digest'):
    print "creating testa.digest"
    f = open("testa.digest", 'w')
    f.write(m.dumps())
    f.close();
  
  m2 = MetaFile('./testa', digest=False)

  f = open("testa.digest", 'r')
  m2.loads(f.read())
  f.close();
  badparts = m2.validate()
  
  print badparts

  #m.dumps('test.digest')
  #print m.dumps()
