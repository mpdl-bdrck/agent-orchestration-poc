"""
Site-wide customization for Python 3.14 async compatibility.

This file is automatically executed by Python before any other modules are imported.
It patches sniffio to handle Python 3.14 compatibility issues with Chainlit/Starlette.

Note: For this to work, you need to either:
1. Place this file in your site-packages directory, OR
2. Set PYTHONPATH to include the directory containing this file, OR  
3. Use the run_chainlit.py wrapper script which handles the patching
"""
import sys

# Only apply patch for Python 3.14+
if sys.version_info >= (3, 14):
    try:
        # Import sniffio modules
        import sniffio._impl
        
        # Store original function from _impl (where it actually lives)
        _original_current_async_library = sniffio._impl.current_async_library
        
        def _patched_current_async_library():
            """Patched version that falls back to 'asyncio' if detection fails."""
            try:
                return _original_current_async_library()
            except sniffio._impl.AsyncLibraryNotFoundError:
                # If detection fails, assume asyncio (most common case)
                return "asyncio"
            except Exception:
                # Catch any other exception as well
                return "asyncio"
        
        # Patch the internal implementation (this is what gets called)
        sniffio._impl.current_async_library = _patched_current_async_library
        
        # Also patch the public API if it exists
        try:
            import sniffio
            sniffio.current_async_library = _patched_current_async_library
        except Exception:
            pass
    except Exception:
        # If patching fails, continue anyway
        pass
