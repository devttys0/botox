#!/usr/bin/env python
import os
from distutils.core import setup, Command
from distutils.dir_util import remove_tree

MODULE_NAME = "botox"
SCRIPT_NAME = MODULE_NAME

class CleanCommand(Command):
    description = "Clean Python build directories"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            remove_tree("build")
        except KeyboardInterrupt as e:
            raise e
        except Exception:
            pass

        try:
            remove_tree("dist")
        except KeyboardInterrupt as e:
            raise e
        except Exception:
            pass

# Install the module, script, and support files
setup(name = MODULE_NAME,
      version = "0.1b",
      description = "ELF patching tool",
      author = "Craig Heffner",
      url = "https://github.com/devttys0/%s" % MODULE_NAME,

      requires = [],
      package_dir = {"" : "src"},
      packages = [MODULE_NAME],
      scripts = [os.path.join("src", "scripts", SCRIPT_NAME)],

      cmdclass = {'clean' : CleanCommand}
)

