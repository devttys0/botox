#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <signal.h>
#include "common.h"
#include "exe.h"

int execute_process(int pid)
{
	int ret_val = 0;

#ifdef EXE
        /* If a path to the gdbserver binary was specified, execute it */
        char exe[FILENAME_MAX] = { 0 };

	#ifdef PIDOPT
        	snprintf((char *) &exe, FILENAME_MAX, "%s %s %s%d", EXE, ARGS, PIDOPT, pid);
	#else
        	snprintf((char *) &exe, FILENAME_MAX, "%s %s", EXE, ARGS);
	#endif
	
        ret_val = system((char *) &exe);

	#ifdef DELAY
        	/* If a delay period was specified, sleep for that period */
        	sleep(DELAY);
	#endif

#endif

	return ret_val;
}

void kill_exe(void)
{
#ifdef EXE
	int pid = 0;

	while((pid = get_process_pid(EXE, 1)) != -1)
	{
		kill(pid, SIGINT);
	}

	usleep(KILL_EXE_SLEEP);
#endif
}
