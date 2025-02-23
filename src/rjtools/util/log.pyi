"""
This type stub file was generated by pyright.
"""

"""
Logging utility to support multiplexing and redirection
"""
class Logger:
    """
    Provides various levels of logging to potentially multiple destinations
    """
    def __init__(self, stdoutFiles=..., stderrFiles=..., debugFiles=..., suppressStandard=...) -> None:
        ...
    
    def info(self, msg, indent=...): # -> None:
        ...
    
    def dbg(self, msg): # -> None:
        ...
    
    def warn(self, msg, indent=...): # -> None:
        ...
    
    def err(self, msg, indent=...): # -> None:
        ...
    


