#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <signal.h>
#include <unistd.h>
#include <getopt.h>

#include "exe.h"
#include "botox.h"

void usage(char *pname)
{
	fprintf(stderr, "\n");
	fprintf(stderr, "Usage: %s [OPTIONS] <process name>\n", pname);
	fprintf(stderr, "\n");
	fprintf(stderr, "\t-p, --pid=<pid>      The minimum pid for the target process [self]\n");
	fprintf(stderr, "\t-t, --time=<uS>      Time to wait before pausing the target process, in micro seconds [0]\n");
	fprintf(stderr, "\t-g, --gdb            Attach gdbserver to the target process\n");
	fprintf(stderr, "\t-h, --help           Show help\n");
	fprintf(stderr, "\n");
}

int main(int argc, char *argv[])
{
	useconds_t ts = 0;
	char *target = NULL;
	pid_t min_pid = getpid();
	int c = 0, pid = 0, gdb = 0, ret_val = EXIT_FAILURE;
	int long_opt_index = 0;
	char *short_options = "p:t:gh";
	struct option long_options[] = {
			{ "pid", required_argument, NULL, 'p' },
			{ "time", required_argument, NULL, 't' },
			{ "gdb", no_argument, NULL, 'g' },
			{ "help", no_argument, NULL, 'h' },
			{ 0, 0, 0, 0 }
        };

	if(argc < 2)
	{
		usage(argv[0]);
		goto end;
	}

	while((c = getopt_long(argc, argv, short_options, long_options, &long_opt_index)) != -1)
	{
		switch(c)
		{
			case 'p':
				min_pid = atoi(optarg);
				break;
			case 't':
				ts = atoi(optarg);
				break;
			case 'g':
				gdb = 1;
				break;
			default:
				usage(argv[0]);
				goto end;
		}
	}

	target = argv[argc-1];

	printf("Waiting for process '%s' with a pid greater than %d\n", target, min_pid);

	while((pid = get_process_pid(target, min_pid)) == -1) { }

	usleep(ts);

	if(kill(pid, SIGSTOP) == -1)
	{
		perror("kill");
	}
	else
	{
		printf("%s (pid %d) has been paused.\n", target, pid);
		if(gdb)
		{
			execute_process(pid);
		}
		ret_val = EXIT_SUCCESS;
	}

end:
	return ret_val;
}

