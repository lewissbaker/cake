#ifndef MODULE_INCLUDED_H
#define MODULE_INCLUDED_H

#if defined(_MSC_VER) || defined(__MWERKS__) || defined(__CWCC__)
  #define MODULEEXPORT __declspec(dllexport)
  #define MODULEIMPORT __declspec(dllimport)
#elif defined(__GNUC__)
  #define MODULEEXPORT __attribute__((dllexport))
  #define MODULEIMPORT __attribute__((dllimport))
#else
  #define MODULEEXPORT
  #define MODULEIMPORT
#endif

#if defined(EXPORT)
  #define MODULEAPI MODULEEXPORT
#elif defined(IMPORT)
  #define MODULEAPI MODULEIMPORT
#else
  #define MODULEAPI
#endif

#endif
