import hashlib
import os
import uuid

from metap2p.trdparty import bencode

class MetaError(Exception):
  pass

#class MetaFile:
#  CHUNKSIZE = 2**20
#  
#  def __init__(self, root, path=None):
#    self.root = root
#    self.hashes = list()
#    self.hash = None
#    self.path = path
#    
#    if path:
#      self.op_path = os.path.join(root, path)
#      
#      if not os.path.isfile(self.op_path):
#        raise MetaError('MetaFile: path is not file - %s'%(self.op_path));
#      
#      f = open(self.op_path, 'r')
#      self._digest_from_file(f);
#      f.close();
#  
#  def _digest_from_file(self, f):
#    m_all = hashlib.new('sha1')
#    
#    last_chunk = False
#    p_s = None
#
#    while True:
#      s = f.read(self.CHUNKSIZE)
#      
#      if len(s) == 0 or not s:
#        break
#      
#      m_all.update(s)
#      m = hashlib.new('sha1', s)
#      self.hashes.append((len(s), m.digest()))
#      del m
#
#    self.hash = m_all.digest();
#    del m_all
#
#  def dumps(self, file=None):
#    
#    if not file:
#      return bencode.bencode(base)
#    else:
#      f = open(file, 'w');
#      f.write(bencode.bencode(base))
#      f.close();
#
#  def _dumps(self):
#    base = dict();
#    base['hashes'] =  self.hashes
#    base['hash'] =    self.hash
#    base['path'] =    self.path
#    return base
#  
#  def _loads(self, base):
#    self.hashes = base['hashes']
#    self.hash   = base['hash']
#  
#  def loads(self, s):
#    base = bencode.bdecode(s)
#    return self._loads(base)
#
#class MetaDir:
#  def __init__(self, root, path=None):
#    self.root = root
#    self.children = list();
#    
#    self.path = path
#    
#    if self.path:
#      self.op_path = os.path.join(root, path)
#      
#      if not os.path.isdir(self.op_path):
#        raise MetaError('MetaDir: is not a directory - %s'%(self.op_path))
#      
#      self._load_from_dir()
#
#  def _load_from_dir(self):
#    for p in os.listdir(self.op_path):
#      subpath = '/'.join([self.path, p])
#      abs_subpath = os.path.join(self.op_path, p)
#      
#      if os.path.isfile(abs_subpath):
#        print "metafile"
#        self.children.append(MetaFile(self.op_path, p))
#        print "metafile end"
#      elif os.path.isdir(abs_subpath):
#        self.children.append(MetaDir(self.op_path, p))
#      
#      print p
#
#  def _dumps(self):
#    base = dict();
#    base['children'] =  map(lambda child: child._dumps(), self.children)
#    base['path'] =      self.path
#    return base
#  
#  def dumps(self):
#    print self._dumps();
#    return bencode.bencode(self._dumps())

class MetaFile:
  CHUNKSIZE=2**20
  SEP='/'
  EXT='cns'
  
  def __init__(self, dir, digest=True, name=None):
    if not os.path.isdir(dir):
      raise MetaError("MetaFile: cannot find base directory")
    
    if name:
      self.name = name
    else:
      self.name = os.path.basename(dir)
    
    self.digest_id = str(uuid.uuid1().hex);
    self.dir = dir
    self.files = list();
    self.dirs = list();
    self.hashes = list();
    self.digestfiles = list();
    self.chunksize = self.CHUNKSIZE
    self.ext = self.EXT
    
    if digest:
      self._digest();
  
  def _digest(self):
    newpaths = list();
    
    for p in os.listdir(self.dir):
      pp = os.path.join(self.dir, p)
      
      if os.path.isfile(pp):
        newpaths.insert(0, (os.path.isdir(pp), pp, p))
    
    dirs = list();
    files = list();
    digestfiles = list();
    
    while True:
      if len(newpaths) == 0:
        break
      
      path = newpaths.pop();
      
      if path[0]:
        dirs.append(path[2])
      else:
        files.append(path[2])
        digestfiles.append((path[1], path[2])) 
      
      if os.path.isdir(path[1]):
        for p in os.listdir(path[1]):
          pp = os.path.join(path[1], p)
          newpaths.insert(0, (os.path.isdir(pp), pp, self.SEP.join((path[2], p))))
    
    self.dirs = dirs
    self.files = files
    self.digestfiles = digestfiles
    
    self._digest_files();

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

    fpath, file = df
    
    f = open(fpath, 'r')
    
    fhash = None
    
    for hash in self.hashes:
      if hash['path'] == file:
        fhash = hash
        break

    if not fhash:
      raise MetaError('Could not find hash for file - %s'%(fpath))

    m_all = hashlib.new('sha1')
    
    cc = 0

    for hash in fhash['hashes']:
      cc += 1
      s = f.read(self.chunksize)
      
      if len(s) == 0 or not s:
        break
      
      m_all.update(s)
      m = hashlib.new('sha1', s)

      if len(s) != hash[0]:
        raise MetaError('File invalid, part %d length invalid - %s'%(cc, fpath))
      
      if m.digest() != hash[1]:
        yield((cc, False))
      else:
        yield((cc, True))
      
      del m
    
    if cc != len(fhash['hashes']):
      raise MetaError('File part count mismatch - %s'%(fpath))
    
    if fhash['digest'] != m_all.digest():
      pass
    
    del m_all
  
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
    self.digestfiles = map(lambda f: (os.path.join(self.dir, f.replace(self.SEP, os.sep)), f), self.files)
  
  def loads(self, base_s):
    return self._loads(bencode.bdecode(base_s))
  
  def validate(self, fn):
    for fpath, fname in self.digestfiles:
      if fn == fname:
        for pp in self._check_file((fpath, fname)):
          yield pp
        return
  
  def filename(self):
    return "%s.%s"%(self.name, self.ext)

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
