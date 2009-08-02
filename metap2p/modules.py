def require_dep(module):
  """
  Try to import a specific module.
  """
  try:
    __import__(module)
  except ImportError, e:
    return False
  
  return True
