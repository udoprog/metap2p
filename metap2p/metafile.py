import hashlib
import os
import uuid

from metap2p.trdparty import bencode

class MetaError(Exception):
  pass

class MetaFile:
  CHUNKSIZE=2**20
  SEP='/'
  EXT='cns'
  
  def __init__(self, dir=None, **kw):
    if dir and not os.path.isdir(dir):
      raise MetaError("MetaFile: cannot find base directory")

    self.digest_id = str(uuid.uuid1().hex);
    self.dir = dir
    self.files = list();
    self.dirs = list();
    self.hashes = list();
    self.digestfiles = list();
    self.chunksize = kw.get('chunksize', self.CHUNKSIZE)
    self.ext = kw.get('ext', self.EXT)
    self.sep = kw.get('sep', self.SEP)
    self.need = None
    
    name = kw.get('name', None)

    from_meta = kw.get('from_meta', None)
    
    if name:
      self.name = name
    elif self.dir:
      self.name = os.path.basename(self.dir)
    else:
      self.name = self.digest_id
    
    if from_meta:
      self._loads(from_meta._dumps())
    elif kw.get('digest', True):
      self._digest();

  def _walk(self, dir):
    newpaths = list();
    
    for p in os.listdir(self.dir):
      pp = os.path.join(self.dir, p)
      
      if (os.path.isfile(pp) or os.path.isdir(pp)) and not os.path.islink(pp):
        newpaths.insert(0, (pp, p))
    
    while True:
      if len(newpaths) == 0:
        break
      
      fpath, fname = newpaths.pop();

      if not os.path.isfile(fpath) and not os.path.isdir(fpath):
        continue
      
      yield (os.path.isdir(fpath), fpath, fname)
      
      if os.path.isdir(fpath):
        for p in os.listdir(fpath):
          pp = os.path.join(fpath, p)
          newpaths.insert(0, (pp, self.SEP.join((fname, p))))
  
  def _digest(self):
    dirs = list();
    files = list();
    digestfiles = list();
    
    for is_dir, fpath, fname in self._walk(self.dir):
      if is_dir:
        dirs.append(fname)
      else:
        files.append(fname)
        digestfiles.append((fpath, fname)) 
    
    self.dirs = dirs
    self.files = files
    self.digestfiles = digestfiles
    
    self._digest_files();

  def _load_digestfiles(self):
    if self.dir:
      return map(lambda f: (os.path.join(self.dir, f.replace(self.SEP, os.sep)), f), self.files)
    else:
      return map(lambda f: (None, f), self.files)
  
  def _digest_files(self):
    hashes = list()
    
    for fpath, file in self.digestfiles:
      fhash = dict(path=file, hashes=list(), digest=None);
      
      f = open(fpath, 'r')
      
      m_all = hashlib.new('sha1')
      
      while True:
        s = f.read(self.chunksize)
        
        if len(s) == 0 or not s:
          break
        
        m_all.update(s)
        m = hashlib.new('sha1', s)
        fhash['hashes'].append((len(s), m.digest()))
        del m
      
      fhash['digest'] = m_all.digest();
      hashes.append(fhash)
    
    self.hashes = hashes
  
  def _check_files(self):
    for fpath, file in self.digestfiles:
      yield((file, list(self._check_file((fpath, file)))))
  
  def _check_file(self, df):
    parts = list()

    fpath, fname = df
    
    f = open(fpath, 'r')
    
    fhash = self._find_hash(fname)
    
    if not fhash:
      raise MetaError('Could not find hash for file - %s'%(fpath))

    m_all = hashlib.new('sha1')
    
    cc = 0
    
    for hash in fhash['hashes']:
      s = f.read(self.chunksize)
      
      if len(s) == 0 or not s:
        break
      
      m_all.update(s)
      
      yield self._validate_chunk(cc, s, hash);
      cc += 1
    
    if cc != len(fhash['hashes']):
      raise MetaError('File part count mismatch - %s'%(fpath))
    
    if fhash['digest'] != m_all.digest():
      pass
    
    del m_all

  def _validate_chunk(self, cc, s, hash):
    m = hashlib.new('sha1', s)

    if len(s) != hash[0]:
      raise MetaError('File invalid, part %d length invalid'%(cc))
    
    digest = m.digest();
    del m
    
    if digest != hash[1]:
      return((cc, False))
    else:
      return((cc, True))
  
  def _dumps(self):
    base = dict();
    base['digest_id'] = self.digest_id
    base['dirs'] = self.dirs
    base['files'] = self.files
    base['hashes'] = self.hashes
    base['chunksize'] = self.chunksize
    base['name'] = self.name
    base['ext'] = self.ext
    base['filename'] = self.filename();
    
    return base

  def dumps(self):
    return bencode.bencode(self._dumps())
  
  def _loads(self, base):
    self.digest_id =  base['digest_id']
    self.name =       base['name']
    self.dirs =       base['dirs']
    self.files =      base['files']
    self.hashes =     base['hashes']
    self.ext =        base['ext']
    
    self.chunksize = base.get('chunksize', self.CHUNKSIZE)
    self.digestfiles = self._load_digestfiles()

  def _find(self, fn):
    for fpath, fname in self.digestfiles:
      if fn == fname:
        return (fpath, fname)

    return None
  
  def _find_hash(self, fn):
    for hh in self.hashes:
      if hh['path'] == fn:
        return hh
    
    return None
  
  def loads(self, base_s):
    return self._loads(bencode.bdecode(base_s))

  def all_valid(self):
    return all(map(lambda f: all(map(lambda fp: fp[1],self.validate(f))), self.files))
  
  def validate(self, fn):
    ff = self._find(fn)

    if not ff:
      return

    for pp in self._check_file(ff):
      yield pp
    
    return
  
  def filename(self):
    return "%s.%s"%(self.name, self.ext)
  
  def read(self, fn, cc):
    ff = self._find(fn)
    fh = self._find_hash(fn)
    
    if not ff:
      return ((-1, False), "")
    
    if not fh:
      raise MetaError('file exists but has not hashtable')
    
    if not (cc >= 0 and cc < len(fh['hashes'])):
      return ((-1, False), "")
    
    fpath, fname = ff
    
    f = open(fpath, 'r')
    f.seek(self.chunksize * cc)
    s = f.read(self.chunksize)
    f.close();
    
    return (self._validate_chunk(cc, s, fh['hashes'][cc]), s)
  
  def write(self, fn, cc, s):
    ff = self._find(fn)
    fh = self._find_hash(fn)
    
    if not ff:
      return (-1, False)
    
    if not fh:
      raise MetaError('file exists but has not hashtable')
    
    if not (cc >= 0 and cc < len(fh['hashes'])):
      return (-1, False)
    
    fpath, fname = ff

    chunk_v = self._validate_chunk(cc, s, fh['hashes'][cc])

    if not chunk_v[1]:
      return chunk_v
    
    f = open(fpath, 'r+')
    f.seek(self.chunksize * cc)
    f.write(s)
    f.close();
    
    return chunk_v

  def create_directories(self):
    for d in self.dirs:
      a_dir = os.path.join(self.dir, d.replace(self.sep, os.sep))
      
      if not os.path.isdir(a_dir):
        print "C", a_dir
        os.mkdir(a_dir)

  def create_skeletons(self, fn=None):
    def single(fn):
      fp, fn =  self._find(fn)
      
      if not os.path.isfile(fp):
        fh =      self._find_hash(fn)
        
        f = open(fp, 'w')
        
        for hash in fh['hashes']:
          f.write("\0" * hash[0])
        
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
      
      # filter valid chunks and map just tuples with (fname, cc)
      needlist = map(lambda cc: cc[0], filter(lambda cc: (not cc[1]), self.validate(fn)))

      if len(needlist) == 0:
        continue
      
      for n in needlist:
        needs.append((fn, n));
    
    return needs

if __name__ == '__main__':
  import sys
  sys.path.append('.')
  
  m = MetaFile('./testa')

  if not os.path.isfile('testa.digest'):
    print "creating testa.digest"
    f = open("testa.digest", 'w')
    f.write(m.dumps())
    f.close()

  m2 = MetaFile('./testa', digest=False)

  f = open("testa.digest", 'r')
  m2.loads(f.read())
  f.close()
  badparts = m2.validate()
  
  print badparts

  #m.dumps('test.digest')
  #print m.dumps()
