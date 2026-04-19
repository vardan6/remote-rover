/*
 * optimus_hint.c — Dual-GPU hint DLL for NVIDIA Optimus / AMD PowerXpress
 *
 * When this DLL is loaded by a process (via ctypes or any other means), the
 * NVIDIA and AMD drivers scan loaded modules for these exported symbols and
 * route WGL (OpenGL) rendering to the discrete GPU instead of the integrated
 * one. This is the standard mechanism used by games and graphics apps.
 *
 * Build (MinGW / MSYS2):
 *   gcc -shared -o optimus_hint.dll optimus_hint.c -Wl,--out-implib,optimus_hint.lib
 *
 * Build (MSVC Developer Command Prompt):
 *   cl /LD optimus_hint.c /link /EXPORT:NvOptimusEnablement /EXPORT:AmdPowerXpressRequestHighPerformance
 *
 * After building, place optimus_hint.dll in the 3d-env\ directory.
 * run.bat will detect and load it automatically before launching the simulator.
 */

#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT
#endif

/* Tell the NVIDIA Optimus driver to select the discrete (high-performance) GPU */
EXPORT unsigned int NvOptimusEnablement = 1;

/* Tell the AMD PowerXpress driver to select the discrete (high-performance) GPU */
EXPORT int AmdPowerXpressRequestHighPerformance = 1;
