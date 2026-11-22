# Checklist del 1/12: entrega, competencia y defensa

Grupo: Nicolás Araneda, Vicente Calderón y Santiago Muñoz.

Entrega en GitHub a las 10:00. Competencia y defensa desde las 10:30. El peldaño que compite se decide con `docs/arbol_decision.md` y lo que se vio el miércoles 25/11, por confirmar (`docs/checklist_26nov.md`).

## 1. Días antes

### 29/11: acceso al repositorio privado

El repositorio `nicolasaraneda/Proyecto4_Arquitectura_De_Computadores` es privado hasta la entrega, porque es una competencia. El profesor y los ayudantes necesitan acceso de lectura **antes de las 10:00 del 1/12**, y GitHub no da el acceso hasta que cada uno acepta la invitación (le llega un correo y queda pendiente hasta que la acepta, hasta 7 días). Por eso se hace el 29/11 y no el mismo día.

1. Pedir al profesor y a cada ayudante su usuario de GitHub (por correo o en clases).
2. Invitar a cada uno con permiso de lectura. Desde la terminal, con la cuenta de `gh` de Nicolás:

   ```
   gh api -X PUT repos/nicolasaraneda/Proyecto4_Arquitectura_De_Computadores/collaborators/USUARIO -f permission=pull
   ```

   `pull` es solo lectura: pueden ver y clonar, no subir cambios (push). Lo mismo por la web: Settings, Collaborators, Add people, elegir el usuario y el rol Read.
3. Comprobar las invitaciones pendientes y los que ya aceptaron:

   ```
   gh api repos/nicolasaraneda/Proyecto4_Arquitectura_De_Computadores/invitations --jq '.[].invitee.login'
   gh api repos/nicolasaraneda/Proyecto4_Arquitectura_De_Computadores/collaborators --jq '.[].login'
   ```

4. El 30/11, si alguno no ha aceptado, escribirle. Plan B si el 1/12 a las 9:30 sigue sin acceso: mandar por correo el enlace del commit etiquetado y el `.zip` que GitHub genera para la etiqueta (`gh release create` no hace falta: el `.zip` de una etiqueta se baja desde la página del repositorio, Code, Download ZIP, estando en la etiqueta).
5. Hoy son colaboradores Nicolás y Vicente (`Vcalderone`). Falta el usuario de Santiago.

Hacerlo público no es la opción: a las 10:00 los demás grupos todavía no han competido.

### 29/11: congelamiento

- Nada que toque `rtl/`, `sw/` o `bitstreams/` después de esta fecha, salvo un juego de contingencia de `retune` que ya esté simulado.
- `make report` y el informe compilado; README revisado; historial con solo la autoría de Nicolás (`git log --format='%an <%ae> | %cn <%ce>' | sort -u`).

### 30/11: ensayo general

- Grabar el peldaño elegido y sus dos respaldos, uno tras otro, con el cronómetro: cuánto demora cada `iceprog` (unos 10 s).
- Ensayo de la defensa con el banco de preguntas (`docs/defensa/`): cada integrante responde preguntas de las piezas que no domina.

## 2. El 1/12 antes de las 10:00

1. `git pull` en `main`. `make check` en verde y la integración continua del último commit en verde (`gh run list --branch main --limit 1`).
2. `cd bitstreams && sha256sum -c SHA256SUMS && cd ..`: todas las líneas en `OK`.
3. Etiquetar la entrega: `git tag -a v-competencia -m "Entrega del Proyecto 4" && git push origin v-competencia`.
4. Comprobar que el profesor y los ayudantes ven el repositorio (sección 1).

## 3. Qué se lleva grabado y qué de respaldo

| Rol | Archivo | Cuándo |
|-----|---------|--------|
| Principal | El peldaño que dé el árbol: `r2_banda40_multi.bin`, `r1_banda40.bin` o `r0_banda40.bin` (banda 40, T140) | Grabado antes de llegar a la sala |
| Respaldo 1 | El peldaño inmediatamente inferior (R1 si compite R2; R0 si compite R1) | Si el principal falla entre rondas |
| Respaldo 2 | `r0_banda40.bin` | Si todo lo demás falla. Ya pasó la puerta de simulación, la de placa y (el miércoles 25/11, por confirmar) la de maestra |
| Contingencia | `bitstreams/contingencia/` | Solo si anuncian otra comisión (árbol, sección 2) |

Se graba con `iceprog bitstreams/ARCHIVO.bin` (Nicolás, con la placa conectada a WSL por `usbipd`); las imágenes múltiples (`r2_banda40_multi.bin` y las demás `*_multi.bin`) con `iceprog -b`, que borra la flash entera. Al terminar debe decir "VERIFY OK".

Con los cables del PMOD puestos y la maestra encendida, desconectar y conectar el USB de la Go Board antes de la primera ronda: los pines del SPI no tienen pull-up, y así la FPGA parte de cero con la maestra ya fijando el nivel de las líneas (`docs/checklist_26nov.md`, sección 2).

## 4. Durante la competencia

- **Entre rondas no se reprograma** si todo funciona: los tres peldaños pasaron las rondas seguidas sin reset en la matriz de estrés, con los tres períodos en los dos órdenes.
- Mirar la telemetría (R1 y R2): el LED de latido cambia con cada precio. Si deja de cambiar con precios llegando, ver `docs/arbol_decision.md`, sección 3.
- Anotar el patrimonio de cada ronda que muestra la pantalla de la maestra.
- Nadie toca los botones de la placa: ningún peldaño los usa, y la regla del mismo programa en las tres rondas se cumple sin ellos.

## 5. Defensa

- Cada integrante debe poder responder sobre cualquier parte (enunciado, sección 5). Reparto y repaso en `docs/defensa/plan_estudio.md`; las cifras de memoria en `docs/defensa/cifras.md`.
- Tener abiertos en el notebook: `README.md`, `docs/puertas.md`, `docs/arbol_decision.md` y el informe en PDF.
- Si preguntan por un número, el comando que lo produce está en el README, en la sección de la pieza.
