from cake.tools import script, env, compiler

compiler.addIncludePath(script.cwd())
compiler.addForcedUsing(
  env.expand('${BUILD}/cppdotnet/assembly/point.dll'),
  )
compiler.addForcedUsingScript(script.cwd("build.cake"))
