#include <Windows.h>
#include <TCHAR.H>
#include <process.h>
#include <stdio.h>

int _tmain(int argc, TCHAR* argv[])
{
	// Get the full path to this executable
	TCHAR executablePath[_MAX_PATH];

	GetModuleFileName(NULL, executablePath, _MAX_PATH);

	// Split the path components
	TCHAR executableDrive[_MAX_DRIVE];
	TCHAR executableDir[_MAX_DIR];
	TCHAR executableName[_MAX_FNAME];
	TCHAR executableExt[_MAX_EXT];

	_tsplitpath(executablePath, executableDrive, executableDir, executableName, executableExt);

	// Build a path to 'cakemain.py' in this exectulable's directory
	TCHAR scriptPath[_MAX_PATH];

	_tmakepath(scriptPath, executableDrive, executableDir, _T("cakemain"), _T(".py"));

	// Build a path to the python.exe, we should be in Python\Scripts so go up one dir
	TCHAR pythonExecutablePath[_MAX_PATH];

	_tmakepath(pythonExecutablePath, executableDrive, executableDir, _T("..\\python"), _T(".exe"));

	// Build the arguments to pass to python
	TCHAR **args = (TCHAR **) malloc((argc + 10) * sizeof(TCHAR *));
	int argi = 0;

	// Add the first argument (the python executable's name)
	args[argi++] = pythonExecutablePath;

	// Set the script to run as the next argument
	args[argi++] = scriptPath;

	// Add the remaining arguments (skip the 1st arg, this executable's name)
	int i = 1;
	for (; i < argc; ++i)
		args[argi++] = argv[i];

	// Terminate the args list
	args[argi++] = NULL;

	// Execute python with our arguments (we should be in Python\Scripts so go up one dir)
	//_texecv(pythonExecutablePath, args);
	_tspawnv(_P_WAIT, pythonExecutablePath, args);

	free(args);

	return 0;
}
