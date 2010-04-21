#ifndef MODULE_INCLUDED_H
#define MODULE_INCLUDED_H

#if defined(_MSC_VER) || defined(__MWERKS__) || defined(__CWCC__)
  #define MODULEEXPORT __declspec(dllexport)
#elif defined(__GNUC__)
  #if __GNUC__ >= 4
    #define MODULEEXPORT __attribute__((visibility("default")))
  #else
    #define MODULEEXPORT __attribute__((dllexport))
  #endif
#else
  #define MODULEEXPORT
#endif

#if defined(EXPORT)
  #define MODULEAPI MODULEEXPORT
#else
  #define MODULEAPI
#endif

#endif
