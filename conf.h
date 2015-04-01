#ifndef __CONF_H__
#define __CONF_H__

/* Path to the executable to run when loaded into the target process */
#ifndef EXE
#define EXE             "gdbserver"
#endif

/* Command line arguments for EXE */
#ifndef ARGS
#define ARGS            "0.0.0.0:1234"
#endif

/* 
 * For processes that require a PID (such as GDB), specify the PID option here 
 * (i.e., "--attach " will result in "--attach <pid>" on the command line) 
 */
#ifndef PIDOPT
#define PIDOPT          "--attach "
#endif

/* Number of seconds to sleep after backgrounding EXE */
#ifndef DELAY
#define DELAY           0
#endif

#endif
