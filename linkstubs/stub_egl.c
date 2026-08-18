#include <EGL/egl.h>
EGLDisplay eglGetCurrentDisplay(void) { return (EGLDisplay)0; }
const char *eglQueryString(EGLDisplay dpy, EGLint name) { return ""; }
void (*eglGetProcAddress(const char *procname))(void) { return (void(*)(void))0; }
EGLint eglGetError(void) { return 0; }
