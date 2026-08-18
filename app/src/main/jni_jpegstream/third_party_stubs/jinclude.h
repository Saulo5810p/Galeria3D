/*
 * jinclude.h
 *
 * Minimal stub matching libjpeg-turbo's own jinclude.h for modern
 * systems: on any ANSI-C platform (which Android/Termux clang is),
 * the only thing the real jinclude.h does is include <stdio.h>
 * before jpeglib.h/jerror.h. Older platform-specific branches
 * (pre-ANSI compilers) are not needed here.
 */

#ifndef JINCLUDE_H
#define JINCLUDE_H

#include <stdio.h>

#endif /* JINCLUDE_H */
