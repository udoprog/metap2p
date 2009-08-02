def require_dep(module, gte=None, gt=None, lte=None, lt=None, eq=None, ne=[]):
  """
  Try to import a specific module.
  """
  def parse_version(version):
    return map(lambda p: int(p), filter(lambda s: s.isdigit(), version.split('.')))

  try:
    m = __import__(module)

    if gte or eq or ne:
      module_version = parse_version(m.__version__)

      if gte:
        assert module_version >= parse_version(gte), (">=", gte)

      if gt:
        assert module_version > parse_version(gte), (">", gt)

      if lte:
        assert module_version <= parse_version(lte), ("lte", lte)

      if lt:
        assert module_version < parse_version(lt), ("lt", lt)
      
      if eq:
        assert module_version == parse_version(ge), ("==", eq)

      if ne:
        for v in ne:
          assert module_version != parse_version(v), ("!=", v)
  except ImportError, e:
    return False
  except AssertionError, e:
    print "Module version mismatch for", module, ' '.join(e), "-- actual version:", m.__version__
    return False
  
  return True

def require_all(dependencies):
  satisfied = True

  for modulename in dependencies:
    basedep = {
      'checks': dict(),
      'message': "You really should define a message..."
    }
    
    dep = dependencies[modulename]
    
    basedep.update(dep)
    
    if basedep.has_key('name'):
      modulename = basedep['name']

    if not require_dep(modulename, **basedep['checks']):
      print basedep['message']
      satisfied = False
  
  return satisfied
