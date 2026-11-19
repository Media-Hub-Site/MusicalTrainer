# MusicalTrainer

**MusicalTrainer** es el conservatorio interactivo de lectura de partituras, teoría musical, instrumentos y entrenamiento auditivo del ecosistema **Media Hub**.

Reimagina y moderniza por completo los entrenadores clásicos de teoría musical con una estética táctil de **Conservatorio & Taller de Luthier** (papel de manuscrito Urtext, nogal, ébano Steinway y bronce), síntesis acústica polifónica en tiempo real y aprendizaje adaptativo.

---

## Disciplinas y Módulos Incluidos

1. **🎼 Lectura de Partitura (`Note Trainer`)**
   - Soporte nativo para **Clave de Sol (2ª)**, **Clave de Fa (4ª)**, **Clave de Do en 3ª (Alto)**, **Clave de Do en 4ª (Tenor)** y **Gran Pentagrama (Sol + Fa)**.
   - Rieles de **Guías Pedagógicas Visuales** con los nombres de cada línea y espacio directamente en la partitura.
   - 3 niveles progresivos (Pentagrama Base, Líneas Adicionales y Cromático de Conservatorio) con algoritmo adaptativo que refuerza tus notas más débiles.
2. **🔑 Armaduras y Tonalidades (`Key Signature Trainer`)**
   - Reconocimiento de las 15 tonalidades Mayores y 15 relativas Menores (0 a 7 sostenidos/bemoles) en cualquier clave.
   - Incluye la rueda interactiva del **🧭 Círculo de Quintas** con reglas mnemotécnicas y escucha del acorde tónico.
3. **📏 Intervalos en Partitura (`Interval Trainer`)**
   - Desde 2ª menor hasta 8ª justa con anclas auditivas de canciones famosas (*Star Wars, Marcha Nupcial, Tiburón, My Way*, etc.).
4. **🎹 Tríadas y Acordes con Inversiones (`Triad & Chord Trainer`)**
   - Tríadas (Mayor, Menor, Disminuido, Aumentado, Sus4) y acordes de Séptima (Maj7, m7, Dominante 7) en Estado Fundamental, 1ª y 2ª Inversión.
5. **🎸 Diapasón de Guitarra y Teclado (`Fretboard & Keyboard Trainer`)**
   - Diapasón interactivo de 6 cuerdas y 13 trastes (`0..12`) sincronizado con el pentagrama y el piano de cola.
6. **👂 Oído Musical (`Ear Trainer`)**
   - Reconocimiento auditivo puro de **Intervalos** (Melódico Ascendente, Melódico Descendente, Armónico), **Acordes** y **Escalas/Modos** (Mayor, Menor Natural, Menor Armónica, Dórico, Mixolidio, Pentatónicas).
7. **🧪 Explorador Libre (`Theory Sandbox`)**
   - Toca cualquier tecla del piano de cola (`C3–G5`), traste de guitarra o acorde/escala para grabarlo en vivo en el pentagrama, escuchar su sonoridad y analizar sus frecuencias en Hz y serie armónica.

---

## Características Distintivas

- **Nomenclatura Triple Instantánea:** Alterna en cualquier momento entre **Dual (`Do · C`)**, **Solfeo Latino (`Do, Re, Mi`)** y **Cifrado Americano (`C, D, E`)**.
- **3 Timbres Acústicos Sintetizados:** Piano de Cola Steinway, Rhodes Eléctrico Vintage y Guitarra/Arpa Acústica (100% nativo en Python sin dependencias pesadas).
- **3 Ambientes Visuales de Estudio:** *Partitura Clásica (Pergamino & Nogal)*, *Steinway Nocturno (Ébano & Bronce)* y *Luthier Sunburst (Caoba & Nácar)*.
- **Metrónomo Mecánico Integrado** (40–208 BPM) y **Modo Reto 60s (Blitz)**.
- **Informe Diagnóstico de Conservatorio** copiable al portapapeles.

---

## Ejecución en Desarrollo

```bash
pip install -r requirements.txt
python main.py --lang=es
```
