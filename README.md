Botox
=====

This tool injects the following code into a Linux ELF file:

```C
kill(getpid(), SIGSTOP);
goto entry_point;
```

When the ELF file is loaded, this will immediately pause execution until a SIGCONT signal is sent to the process, at which point execution resumes from the ELF's original entry point.
This provides time to attach to the process with a debugger and analyze entries in the /proc/pid directory before resuming execution.

Why might this be useful?

1. You wish to debug a process that is executed by another process (e.g., a CGI file executed by a Web server).
2. You want to examine the memory layout (`/proc/pid/maps`) of a short-lived process without requiring a debugger.
3. You wish to debug a process, but starting the process from inside a debugger can modify process environment variables, stack offsets, etc.

These goals are not always easily realized via traditional methods, especially on embedded systems where you may have limited access to debugging tools / toolchains.

Usage
=====

Simply provide the path to the ELF binary you wish to modify, and Botox will add the SIGSTOP code to it:

```bash
$ botox ./path/to/some/file.cgi
```

Supported Architectures
=======================

Botox currently supports x86, x86_64, ARM and MIPS executable, non-relocatable, ELF files. Note that only x86 has been thoroughly tested, but what could possibly go wrong?!

Installation
============

Just run the included `setup.py` installation script:

```bash
$ sudo python2 setup.py install
```

Dependencies
============

Botox is written in Python, and requires the [keystone assembler](http://www.keystone-engine.org/) library and Python module.

