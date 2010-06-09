#ifndef MODULE_INCLUDED_H
#define MODULE_INCLUDED_H

#if defined(_MSC_VER) || defined(__MWERKS__) || defined(__CWCC__)
  #define EXPORT_API __declspec(dllexport)
#elif defined(__GNUC__)
  #if __GNUC__ >= 4
    #define EXPORT_API __attribute__((visibility("default")))
  #else
    #define EXPORT_API __attribute__((dllexport))
  #endif
#else
  #define EXPORT_API
#endif

#if !defined(EXPORT_MODULE)
  #define EXPORT_MODULE 0
#endif

#if EXPORT_MODULE == 1
  #define MODULE_API EXPORT_API
#else
  #define MODULE_API
#endif

#endif
