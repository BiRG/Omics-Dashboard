
#!/bin/sh
cat app/environments/environment.ts | sed -E "s|(omicsUrl: )'(.*)'|\1'$OMICSSERVER'|g;" > app/environments/environment.ts
cat app/environments/environment.prod.ts | sed -E "s|(omicsUrl: )'(.*)'|\1'$OMICSSERVER'|g;" > app/environments/environment.prod.ts
ng serve
