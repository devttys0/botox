#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <dirent.h>

#include "exe.h"
#include "common.h"

/* Some stripped libc's don't have symbol __xpg_basename */
char *_my_basename(char *file)
{
        int i = 0;
        char *ptr = NULL;

        for(i=strlen(file)-1; i>=0; i--)
        {
                ptr = file + i;
                if(ptr[0] == '/')
                {
                        ptr++;
                        break;
                }
        }

        return ptr;
}

int get_process_pid(char *target, int min_pid)
{
	DIR *proc_dir = NULL;
        struct dirent *proc_dir_info = NULL;
        char pname[FILENAME_MAX] = { 0 }, exe_path[FILENAME_MAX] = { 0 };
	int pid = 0, r_pid = -1, target_len = 0;

	target_len = strlen(target);

        /* Open the /proc directory */
        proc_dir = opendir(PROC);
        if(!proc_dir)
        {
                perror("opendir");
                goto end;
        }

        /* Loop through each entry in /proc */
        while((proc_dir_info = readdir(proc_dir)) != NULL)
        {
                /* If the file name inside of /proc is a number, it's probably a PID directory. */
		pid = atoi(proc_dir_info->d_name);
                if(pid > min_pid)
		{
			memset((void *) &exe_path, 0, FILENAME_MAX);
			memset((void *) &pname, 0, FILENAME_MAX);

			snprintf((char *) &exe_path, FILENAME_MAX, "%s/%d/exe", PROC, pid);

			if(readlink((char *) &exe_path, (char *) &pname, FILENAME_MAX) != -1)
        		{
                		if(memcmp(_my_basename((char *) &pname), target, target_len) == 0)
				{
					r_pid = pid;
//					printf("%s -> %s\n", (char *) &exe_path, (char *) &pname);
					break;
				}
        		}
		}
	}

end:
	if(proc_dir) closedir(proc_dir);
	return r_pid;
}


