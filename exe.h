#ifndef __EXE_H__
#define __EXE_H__

#include "conf.h"

#define KILL_EXE_SLEEP	250000	// uSeconds

/* Executes EXE. pid is used for the argument to PIDOPT, if defined. */
int execute_process(int pid);
void kill_exe(void);

#endif
