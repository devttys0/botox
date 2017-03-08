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

1. You wish to debug a process, but starting the process from inside a debugger can modify process enviroment variables, stack offsets, etc.
2. You wish to debug a process that is executed by another process (e.g., a CGI file executed by a Web server).
3. You want to examine the memory layout (/proc/pid/maps) of a short-lived process without requiring a debugger.

These goals are not always easily realized via traditional methods, especially on embedded systems where you may have limited access to debugging tools / toolchains.

Usage
=====

Simply provide the path to the ELF binary you wish to modify, and Botox will add the SIGSTOP code to it:

```bash
$ botox ./path/to/some/file.cgi

Installation
============

Just run the included `setup.py` installation script:

```bash
$ sudo python2 setup.py install
```
```
Dependencies
============

Botox is written in Python, and requires the [keystone assembler](http://www.keystone-engine.org/) library and Python module.

