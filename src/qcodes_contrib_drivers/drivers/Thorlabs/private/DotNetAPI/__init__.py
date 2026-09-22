try:
    import clr
except ImportError:
    print("Could not import 'clr'. Please install the 'pythonnet' package by running: pip install pythonnet")
    raise  # re-raise the ImportError after printing the message
