#!/usr/bin/env python3
"""
Wrapper script to run Chainlit with Python 3.14 async compatibility fixes.

CRITICAL: This script MUST be used for Python 3.14+ to avoid async context errors.
It patches sniffio BEFORE Chainlit imports anything.
"""
import sys
import os

# CRITICAL: Patch sniffio BEFORE importing ANYTHING else
# This must happen before any async libraries are imported
if sys.version_info >= (3, 14):
    # Patch sniffio._impl directly at the module level
    try:
        # Import sniffio modules BEFORE any other imports
        import sniffio._impl
        
        # Store original function
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
        
        print("✅ Applied sniffio patch for Python 3.14 compatibility")
    except Exception as e:
        print(f"⚠️ Warning: Failed to patch sniffio: {e}")
        print("Continuing anyway...")

# Apply nest_asyncio for reentrant event loops
try:
    import nest_asyncio
    nest_asyncio.apply()
    print("✅ Applied nest_asyncio for async compatibility")
except Exception as e:
    print(f"⚠️ Warning: Failed to apply nest_asyncio: {e}")

# Now import and run chainlit
if __name__ == "__main__":
    # Ensure we're in the right directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Verify app.py exists
    if not os.path.exists("app.py"):
        print("❌ Error: app.py not found in current directory")
        sys.exit(1)
    
    # Import chainlit CLI and run
    try:
        # Import chainlit CLI module directly (patches are already applied)
        # The app.py file also has patches, so this should work
        from chainlit import cli
        
        print(f"🚀 Starting Chainlit server...")
        print(f"📁 Working directory: {script_dir}")
        print(f"🐍 Python version: {sys.version}")
        print(f"📝 App file: app.py")
        print("")
        
        # Set up sys.argv for chainlit CLI
        sys.argv = ["chainlit", "run", "app.py", "-w"]
        
        # Run chainlit CLI
        cli.chainlit_run()
    except ImportError as e:
        print(f"❌ Error: Chainlit not installed: {e}")
        print("Install with: pip install chainlit")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting Chainlit: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
