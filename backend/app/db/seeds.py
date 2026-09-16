"""Catálogos iniciales del policlínico: especialidades y tarifario.

Los precios se transcriben del libro «TARIFARIO 2026» que el establecimiento
mantiene en Excel (`fomato_clinicasatipo/Tarifarios`), de modo que el sistema
arranque con el mismo tarifario que ya se cobra en caja y no con una muestra
inventada. Criterios de la transcripción:

* el precio es el de lista al público, en soles, con el material básico ya
  incluido cuando la hoja original lo indica así;
* cuando la hoja da un rango («2 a 4 sesiones, 100-200») o dos columnas de
  «desde / hasta», se carga el extremo inferior y el nombre deja constancia del
  alcance: subirlo es una decisión comercial, no de transcripción;
* el traslado en ambulancia se carga con la tripulación estándar (licenciada y
  conductor) y, en los destinos largos, también la variante con médico.

La carga es incremental e idempotente: al arrancar solo se agregan las
especialidades y los códigos que faltan. Un precio ya ajustado a mano desde el
módulo de configuración nunca se pisa, y un servicio que el administrador
desactivó no reaparece.
"""

import logging
from decimal import Decimal
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import MedicalService, ServiceKind, Specialty

logger = logging.getLogger(__name__)

# (nombre, descripción, duración por defecto en minutos)
SPECIALTIES: tuple[tuple[str, str, int], ...] = (
    ("Medicina General", "Consulta médica ambulatoria", 20),
    ("Obstetricia", "Control prenatal y salud de la mujer", 30),
    ("Odontología", "Atención dental y profilaxis", 30),
    ("Pediatría", "Atención de niñas y niños", 20),
    ("Optometría", "Evaluación visual y medidas ópticas", 30),
    ("Laboratorio", "Toma de muestras y análisis clínicos", 15),
    ("Rayos X", "Estudios radiológicos", 20),
    ("Enfermería / Tópico", "Triaje, curaciones e inyectables", 15),
    ("Medicina Interna", "Consulta de especialidad en adultos", 30),
    ("Ginecología", "Salud ginecológica y procedimientos", 30),
    ("Cirugía General", "Cirugía menor y procedimientos de sala", 45),
    ("Traumatología", "Fracturas, yesos y férulas", 30),
    ("Ecografía", "Estudios ultrasonográficos", 30),
    ("Terapia Física y Rehabilitación", "Fisioterapia y terapia del lenguaje", 45),
    ("Psicología", "Evaluación, tamizaje y psicoterapia", 45),
    ("Psiquiatría", "Consulta de salud mental", 45),
    ("Geriatría", "Atención del adulto mayor", 30),
    ("Medicina Estética", "Procedimientos estéticos no quirúrgicos", 45),
)


# (nombre, precio) o (nombre, precio, especialidad propia). El tercer elemento
# se usa cuando el ítem comparte tipo y duración con su bloque pero lo atiende
# otro servicio: las consultas, por ejemplo, van juntas en el tarifario y cada
# una pertenece a su especialidad.
TariffItem = tuple[str, str] | tuple[str, str, str]


class Tariff(NamedTuple):
    """Bloque del tarifario: comparte tipo, especialidad y duración.

    El código de cada servicio se arma con el prefijo del bloque y la posición
    dentro de él (`LAB-014`), así que los ítems nuevos se agregan **al final**
    del bloque: insertarlos en medio correría los códigos de los que siguen y
    el catálogo ya instalado quedaría desalineado con el del código fuente.
    """

    prefix: str
    kind: ServiceKind
    specialty: str | None
    duration: int
    items: tuple[TariffItem, ...]


# Códigos de la primera versión del catálogo. Estos servicios ya existen con
# ese código en las bases instaladas, de modo que se respeta para que recargar
# el tarifario no duplique la fila.
LEGACY_CODES: dict[str, str] = {
    "Consulta de medicina general": "CON-GEN",
    "Consulta obstétrica": "CON-OBS",
    "Consulta odontológica": "CON-ODO",
    "Consulta pediátrica": "CON-PED",
    "Evaluación optométrica": "CON-OPT",
    "Hemograma completo": "LAB-HEM",
    "Glucosa en ayunas": "LAB-GLU",
    "Radiografía de tórax": "RX-TOR",
    "Aplicación de inyectable": "TOP-INY",
    "Curación simple": "TOP-CUR",
}


CONSULTAS = Tariff("CON", ServiceKind.CONSULTA, "Medicina General", 20, (
    ("Consulta de medicina general", "40.00"),
    ("Atención de emergencia diurna", "120.00"),
    ("Atención de emergencia nocturna", "150.00"),
    ("Consulta domiciliaria con apertura de historia clínica", "200.00"),
    ("Triaje", "10.00", "Enfermería / Tópico"),
))

CONSULTAS_ESPECIALIDAD = Tariff("CES", ServiceKind.CONSULTA, "Medicina Interna", 30, (
    ("Consulta de especialidad (medicina interna, cirugía, traumatología o ginecología)", "100.00"),
    ("Consulta de geriatría", "150.00", "Geriatría"),
    ("Consulta de psiquiatría", "250.00", "Psiquiatría"),
    ("Consulta pediátrica", "100.00", "Pediatría"),
    ("Consulta obstétrica", "100.00", "Obstetricia"),
    ("Consulta odontológica", "60.00", "Odontología"),
    ("Consulta con cirujano maxilofacial", "100.00", "Odontología"),
    ("Consulta psicológica", "50.00", "Psicología"),
    ("Consulta de medicina física y rehabilitación", "30.00", "Terapia Física y Rehabilitación"),
    ("Evaluación quirúrgica compleja con plan de tratamiento", "200.00", "Odontología"),
))

ADMINISTRATIVOS = Tariff("ADM", ServiceKind.OTRO, None, 15, (
    ("Certificado médico", "80.00"),
    ("Formato para certificado médico", "25.00"),
    ("Certificado de salud física (radiografía, electrocardiograma y consulta)", "270.00"),
    ("Certificado de salud mental con psiquiatra", "250.00"),
    ("Certificado psicológico", "90.00"),
    ("Certificado psicológico para descartar necesidades especiales", "150.00"),
    ("Certificado de lucidez mental", "100.00"),
    ("Certificado prenupcial (VDRL, AHC, VIH, radiografía de tórax y grupo sanguíneo)", "217.00"),
    ("Certificado de defunción", "500.00"),
    ("Constancia de atención", "40.00"),
    ("Informe médico", "80.00"),
    ("Informe radiológico", "80.00"),
    ("Epicrisis", "80.00"),
    ("Búsqueda de historia clínica", "40.00"),
    ("Duplicado de historia clínica", "40.00"),
    ("Copia de documento de identidad", "0.50"),
    ("Observación sin monitor por hora", "10.00"),
    ("Observación sin monitor de 7 a 12 horas", "70.00"),
    ("Observación con monitor por hora", "15.00"),
    ("Observación con monitor de 7 a 12 horas", "100.00"),
    ("Administración de oxígeno por balón grande", "450.00"),
    ("Concentrador de oxígeno por hora", "20.00"),
    ("Concentrador de oxígeno por día", "100.00"),
    ("Alquiler de monitoreo de presión arterial por 24 horas", "200.00"),
    ("Control de presión arterial", "3.00"),
    ("Control de presión arterial y saturación", "8.00"),
    ("Control de saturación de oxígeno", "5.00"),
    ("Control de peso y talla", "2.00"),
    ("Prueba de sensibilidad", "5.00"),
))

HOSPITALIZACION = Tariff("HOS", ServiceKind.OTRO, None, 60, (
    ("Hospitalización general por día", "150.00"),
    ("Hospitalización con monitor por día", "180.00"),
    ("Hospitalización con colchón antiescaras por día", "180.00"),
    ("Hospitalización con colchón antiescaras y monitor por día", "210.00"),
    ("Internamiento", "400.00"),
    ("Kit de materiales de hospitalización por día", "30.00"),
    ("Kit de aseo del paciente hospitalizado", "30.00"),
    ("Higiene total del paciente", "30.00"),
    ("Aspiración y asistencia de enfermera adicional", "50.00"),
    ("Uso de sala para cirugía menor", "100.00"),
    ("Kit de materiales de sala para cirugía menor", "37.50"),
))

INYECTABLES = Tariff("INY", ServiceKind.PROCEDIMIENTO, "Enfermería / Tópico", 15, (
    ("Aplicación de inyectable", "6.00"),
    ("Inyectable subcutáneo", "6.00"),
    ("Inyectable endovenoso", "50.00"),
    ("Retiro de vía endovenosa", "12.00"),
))

VACUNAS = Tariff("VAC", ServiceKind.PROCEDIMIENTO, "Enfermería / Tópico", 15, (
    ("Vacuna contra la hepatitis B", "60.00"),
    ("Vacuna contra sarampión, rubéola y parotiditis", "50.00"),
    ("Vacuna contra la poliomielitis", "75.00"),
    ("Vacuna contra la influenza", "75.00"),
    ("Vacuna contra la fiebre amarilla", "80.00"),
    ("Vacuna antirrábica", "140.00"),
    ("Vacuna antitetánica", "55.00"),
    ("Vacuna diftérica y tetánica", "55.00"),
))

LABORATORIO = Tariff("LAB", ServiceKind.LABORATORIO, "Laboratorio", 15, (
    ("Hemograma completo", "47.00"),
    ("Glucosa en ayunas", "17.00"),
    ("Glucosa post prandial", "17.00"),
    ("Glucosa en orina", "17.00"),
    ("Test de tolerancia a la glucosa", "50.00"),
    ("Hemoglobina", "12.00"),
    ("Hematocrito", "12.00"),
    ("Hemoglobina y hematocrito", "17.00"),
    ("Constantes corpusculares", "17.00"),
    ("Lámina periférica", "47.00"),
    ("Recuento de plaquetas", "47.00"),
    ("Recuento de reticulocitos", "30.00"),
    ("Recuento de leucocitos", "15.00"),
    ("Recuento de eosinófilos", "15.00"),
    ("Velocidad de sedimentación globular (VSG)", "17.00"),
    ("Velocidad de sedimentación por Westergren", "15.00"),
    ("Grupo sanguíneo y factor Rh", "12.00"),
    ("Tiempo de coagulación", "15.00"),
    ("Tiempo de sangría", "15.00"),
    ("Tiempo de protrombina con INR", "40.00"),
    ("Tiempo de trombina", "40.00"),
    ("Tiempo de tromboplastina parcial (TTP)", "40.00"),
    ("Dímero D", "80.00"),
    ("Ferritina", "80.00"),
    ("Hierro sérico", "80.00"),
    ("Transferrina", "70.00"),
    ("Test de Coombs directo", "50.00"),
    ("Test de Coombs indirecto", "50.00"),
    ("Células LE", "20.00"),
    ("Fenómeno LE", "47.00"),
    ("Urea", "18.00"),
    ("Creatinina", "17.00"),
    ("Ácido úrico", "28.00"),
    ("Colesterol total", "17.00"),
    ("Colesterol HDL", "20.00"),
    ("Colesterol LDL", "20.00"),
    ("Colesterol VLDL", "20.00"),
    ("Triglicéridos", "18.00"),
    ("Perfil lipídico", "64.00"),
    ("Perfil hepático", "150.00"),
    ("Perfil renal", "118.00"),
    ("Perfil pancreático", "65.00"),
    ("Hemoglobina glicosilada", "70.00"),
    ("Amilasa", "39.00"),
    ("Lipasa", "37.00"),
    ("Albúmina", "25.00"),
    ("Proteínas totales y fraccionadas", "40.00"),
    ("Bilirrubina total", "40.00"),
    ("Bilirrubina directa", "40.00"),
    ("Bilirrubina indirecta", "40.00"),
    ("Bilirrubina total y fraccionada", "40.00"),
    ("Fosfatasa alcalina", "28.00"),
    ("Transaminasa TGO", "20.00"),
    ("Transaminasa TGP", "20.00"),
    ("Gamma glutamil transpeptidasa (GGT)", "32.00"),
    ("Deshidrogenasa láctica (DHL)", "22.00"),
    ("CPK total", "85.00"),
    ("CPK MB", "85.00"),
    ("Troponina T", "110.00"),
    ("Calcio sérico", "60.00"),
    ("Calcio iónico", "90.00"),
    ("Calcio en orina de 24 horas", "40.00"),
    ("Fósforo", "40.00"),
    ("Magnesio", "60.00"),
    ("Litio", "140.00"),
    ("Electrolitos en orina", "120.00"),
    ("Ácido fólico", "75.00"),
    ("Vitamina B12", "110.00"),
    ("Análisis de gases arteriales (AGA)", "120.00"),
    ("Examen completo de orina", "15.00"),
    ("Sedimento de orina", "10.00"),
    ("Reacción inflamatoria", "15.00"),
    ("Proteínas en orina cualitativo", "37.00"),
    ("Proteinuria de 24 horas cuantitativa", "60.00"),
    ("Ácido úrico en orina de 24 horas", "28.00"),
    ("Depuración de creatinina en orina de 24 horas", "28.00"),
    ("Proteinograma electroforético en orina de 24 horas", "130.00"),
    ("Parasitológico simple con envase", "12.00"),
    ("Parasitológico seriado por tres muestras", "27.00"),
    ("Coprológico funcional", "45.00"),
    ("Coprocultivo y antibiograma", "100.00"),
    ("Grasas en heces", "15.00"),
    ("Sustancias reductoras en heces", "15.00"),
    ("Thevenon (sangre oculta en heces)", "35.00"),
    ("Rotavirus en heces", "45.00"),
    ("Test de Graham para oxiuros", "15.00"),
    ("Aglutinaciones en lámina", "20.00"),
    ("Aglutinaciones en tubo", "30.00"),
    ("Brucella rosa de bengala", "20.00"),
    ("RPR / VDRL cualitativo", "35.00"),
    ("RPR / VDRL cuantitativo", "90.00"),
    ("Antiestreptolisinas ASO cualitativo", "27.00"),
    ("Antiestreptolisinas ASO cuantitativo", "45.00"),
    ("Factor reumatoideo cualitativo", "22.00"),
    ("Factor reumatoideo cuantitativo", "80.00"),
    ("Proteína C reactiva cualitativa", "30.00"),
    ("Proteína C reactiva cuantitativa", "60.00"),
    ("Anticuerpos antinucleares (ANA)", "80.00"),
    ("Prueba rápida de VIH", "45.00"),
    ("VIH por ELISA", "90.00"),
    ("Antígeno australiano HBsAg", "45.00"),
    ("Antígeno de hepatitis B AgHBe", "45.00"),
    ("Hepatitis A IgM", "90.00"),
    ("Hepatitis A IgG", "90.00"),
    ("Hepatitis B anticore total", "90.00"),
    ("Hepatitis C (anticuerpos anti VHC)", "90.00"),
    ("Herpes virus tipo 1 IgM", "90.00"),
    ("Herpes virus tipo 2 IgM", "90.00"),
    ("Toxoplasma IgG", "90.00"),
    ("Toxoplasma IgM", "90.00"),
    ("Citomegalovirus IgG", "90.00"),
    ("Citomegalovirus IgM", "90.00"),
    ("Rubéola IgG", "90.00"),
    ("Rubéola IgM", "90.00"),
    ("Inmunoglobulina sérica IgE", "90.00"),
    ("Inmunoglobulina sérica IgA", "90.00"),
    ("Inmunoglobulina sérica IgG", "90.00"),
    ("Inmunoglobulina sérica IgM", "90.00"),
    ("Cisticercosis", "240.00"),
    ("Beta 2 microglobulina", "130.00"),
    ("Prueba rápida de dengue", "45.00"),
    ("Prueba rápida de COVID-19", "70.00"),
    ("Antígeno de COVID-19", "100.00"),
    ("Helicobacter pylori prueba rápida", "40.00"),
    ("Helicobacter pylori IgG", "90.00"),
    ("Helicobacter pylori en heces", "47.00"),
    ("TBC en sangre", "35.00"),
    ("Prueba de embarazo en orina", "15.00"),
    ("HCG en sangre cualitativo", "25.00"),
    ("HCG beta en sangre cuantitativo", "60.00"),
    ("TSH ultrasensible", "90.00"),
    ("T3 libre", "90.00"),
    ("T3 total", "90.00"),
    ("T4 libre", "90.00"),
    ("T4 total", "90.00"),
    ("Tiroglobulina", "100.00"),
    ("Hormona folículo estimulante (FSH)", "90.00"),
    ("Hormona luteinizante (LH)", "90.00"),
    ("Estradiol libre", "90.00"),
    ("Progesterona", "90.00"),
    ("Prolactina", "90.00"),
    ("PSA total", "90.00"),
    ("PSA libre", "90.00"),
    ("PSA total prueba rápida", "35.00"),
    ("Antígeno carcinoembrionario (CEA)", "120.00"),
    ("Marcador tumoral CA 15-3 (mama)", "120.00"),
    ("Marcador tumoral CA 125 (ovario)", "120.00"),
    ("Marcador tumoral CA 19-9", "140.00"),
    ("Marcador tumoral CA 72-4 (estómago)", "180.00"),
    ("Alfafetoproteína (AFP)", "105.00"),
    ("Adenosín deaminasa (ADA)", "90.00"),
    ("Urocultivo y antibiograma", "100.00"),
    ("Urocultivo con removedor de antibiótico", "100.00"),
    ("Hemocultivo", "100.00"),
    ("Cultivo de secreción", "100.00"),
    ("Cultivo de herida", "100.00"),
    ("Cultivo de hongos", "100.00"),
    ("Examen directo y coloración Gram", "60.00"),
    ("Coloración Gram de secreciones", "25.00"),
    ("Coloración Giemsa", "12.00"),
    ("Frotis y examen directo", "17.00"),
    ("Examen directo con KOH para hongos", "30.00"),
    ("Gota gruesa para paludismo", "25.00"),
    ("Leishmaniasis con material", "30.00"),
    ("Examen de esputo por una muestra", "25.00"),
    ("Examen de esputo por tres muestras", "65.00"),
    ("Cultivo de secreción faríngea", "110.00"),
    ("Análisis de muestra articular", "180.00"),
    ("Papanicolaou con material", "60.00"),
    ("Test de helecho", "27.00"),
    ("Test de ácaros", "30.00"),
    ("Análisis de alergia", "50.00"),
))

RAYOS_X = Tariff("RX", ServiceKind.IMAGENES, "Rayos X", 20, (
    ("Radiografía de tórax", "60.00"),
    ("Radiografía de tórax frontal y lateral", "75.00"),
    ("Radiografía toracoabdominal", "65.00"),
    ("Radiografía de corazón y grandes vasos", "55.00"),
    ("Radiografía de descarte escolar de tuberculosis", "50.00"),
    ("Radiografía de abdomen simple de pie", "55.00"),
    ("Radiografía de abdomen simple en decúbito", "65.00"),
    ("Radiografía de abdomen de decúbito y de pie", "80.00"),
    ("Radiografía de cráneo frontal y lateral", "60.00"),
    ("Radiografía de senos paranasales", "60.00"),
    ("Radiografía de macizo facial", "70.00"),
    ("Radiografía de huesos de la cara", "70.00"),
    ("Radiografía de huesos de la cara para fines legales", "200.00"),
    ("Radiografía de huesos propios de la nariz", "70.00"),
    ("Radiografía de huesos propios de la nariz para fines legales", "200.00"),
    ("Radiografía de maxilar superior", "60.00"),
    ("Radiografía de maxilar inferior", "60.00"),
    ("Radiografía de articulación temporomandibular por lado", "60.00"),
    ("Radiografía de articulación temporomandibular comparativa", "85.00"),
    ("Radiografía de mastoides por lado", "65.00"),
    ("Radiografía de mastoides comparativa", "75.00"),
    ("Radiografía de peñascos por lado", "55.00"),
    ("Radiografía de peñascos comparativos", "70.00"),
    ("Radiografía de silla turca", "65.00"),
    ("Radiografía de cavum faríngeo", "65.00"),
    ("Radiografía de órbitas unilaterales", "60.00"),
    ("Radiografía de columna cervical frontal y lateral", "55.00"),
    ("Radiografía de columna cervical oblicuas", "70.00"),
    ("Radiografía de columna cervical funcional", "95.00"),
    ("Radiografía de columna cervicodorsal", "60.00"),
    ("Radiografía de columna dorsal", "60.00"),
    ("Radiografía de columna dorsolumbar", "100.00"),
    ("Radiografía de columna lumbar", "60.00"),
    ("Radiografía de columna lumbar oblicuas", "70.00"),
    ("Radiografía de columna lumbar funcional", "95.00"),
    ("Radiografía de columna lumbosacra", "65.00"),
    ("Radiografía de columna sacrococcígea", "65.00"),
    ("Radiografía de coxis", "60.00"),
    ("Radiografía de columna panorámica en niños", "75.00"),
    ("Radiografía de pelvis", "65.00"),
    ("Radiografía de pelvis y cadera", "105.00"),
    ("Radiografía de pelvis incidencia de Ferguson", "60.00"),
    ("Radiografía de pelvis Von Rosen sin informe", "75.00"),
    ("Radiografía de pelvis Von Rosen con informe", "170.00"),
    ("Radiografía de cadera unilateral", "55.00"),
    ("Radiografía de caderas comparativas", "80.00"),
    ("Radiografía de articulación coxofemoral unilateral", "65.00"),
    ("Radiografía de articulación coxofemoral comparativa", "85.00"),
    ("Radiografía de articulación sacroilíaca", "60.00"),
    ("Radiografía de articulaciones sacroilíacas comparativas", "85.00"),
    ("Radiografía de clavícula", "55.00"),
    ("Radiografía de clavículas comparativas", "85.00"),
    ("Radiografía de escápula", "50.00"),
    ("Radiografía de hombro frontal por lado", "55.00"),
    ("Radiografía de hombro unilateral transtorácica", "70.00"),
    ("Radiografía de hombros comparativos", "95.00"),
    ("Radiografía de hombros funcionales con rotación", "95.00"),
    ("Radiografía de esternón", "60.00"),
    ("Radiografía de parrilla costal por lado", "65.00"),
    ("Radiografía de parrilla costal comparativa", "80.00"),
    ("Radiografía de brazo unilateral", "55.00"),
    ("Radiografía de brazos comparativos", "85.00"),
    ("Radiografía de codo unilateral", "55.00"),
    ("Radiografía de codos comparativos", "65.00"),
    ("Radiografía de antebrazo unilateral", "50.00"),
    ("Radiografía de antebrazos comparativos", "85.00"),
    ("Radiografía de muñeca unilateral", "50.00"),
    ("Radiografía de muñecas comparativas", "75.00"),
    ("Radiografía de mano unilateral", "50.00"),
    ("Radiografía de manos comparativas", "80.00"),
    ("Radiografía de edad ósea", "55.00"),
    ("Radiografía de fémur unilateral", "60.00"),
    ("Radiografía de fémures comparativos", "85.00"),
    ("Radiografía de rodilla unilateral", "50.00"),
    ("Radiografía de rodillas comparativas", "80.00"),
    ("Radiografía de rótula unilateral", "50.00"),
    ("Radiografía de rótulas comparativas", "85.00"),
    ("Radiografía de pierna unilateral", "60.00"),
    ("Radiografía de piernas comparativas", "100.00"),
    ("Radiografía de tobillo unilateral", "50.00"),
    ("Radiografía de tobillos comparativos", "75.00"),
    ("Radiografía de calcáneo unilateral", "50.00"),
    ("Radiografía de calcáneos comparativos", "85.00"),
    ("Radiografía de pie unilateral", "50.00"),
    ("Radiografía de pies comparativos", "75.00"),
    ("Medición de miembros inferiores en niños", "120.00"),
    ("Medición de miembros inferiores en adultos", "170.00"),
    ("Esófago, estómago y duodeno con contraste", "700.00"),
    ("Esofagograma con contraste", "570.00"),
    ("Tránsito intestinal con contraste", "570.00"),
    ("Colon por doble contraste", "420.00"),
    ("Urografía excretora", "380.00"),
    ("Urografía retrógrada", "390.00"),
    ("Histerosalpingografía", "430.00"),
    ("Fistulografía", "85.00"),
    ("Fetografía", "200.00"),
    ("Placa radiográfica adicional", "15.00"),
    ("Impresión de placa para carné sanitario o prenupcial", "50.00"),
    ("Grabación de estudio en DVD", "20.00"),
    ("Lectura e informe de radiografía", "85.00"),
))

DENSITOMETRIA = Tariff("DEN", ServiceKind.IMAGENES, "Rayos X", 30, (
    ("Densitometría ósea de antebrazo", "75.00"),
    ("Densitometría ósea de columna lumbar", "120.00"),
    ("Densitometría ósea de pelvis", "120.00"),
    ("Densitometría ósea de columna lumbar y pelvis", "225.00"),
    ("Densitometría ósea de columna lumbar y antebrazo", "210.00"),
    ("Densitometría ósea de cuerpo entero", "305.00"),
))

ECOGRAFIA = Tariff("ECO", ServiceKind.IMAGENES, "Ecografía", 30, (
    ("Ecografía abdominal", "90.00"),
    ("Ecografía abdominal completa", "150.00"),
    ("Ecografía renal", "90.00"),
    ("Ecografía prostática", "90.00"),
    ("Ecografía transvaginal", "150.00"),
    ("Ecografía pélvica", "150.00"),
    ("Ecografía obstétrica", "150.00"),
    ("Ecografía genética de 11 a 12 semanas", "210.00"),
    ("Ecografía morfológica de 15 a 21 semanas", "210.00"),
    ("Monitoreo ovulatorio (cuatro ecografías)", "220.00"),
    ("Ecografía de cadera bilateral en lactantes", "150.00"),
    ("Ecografía de mamas", "150.00"),
    ("Ecografía de partes blandas", "150.00"),
    ("Ecografía de articulación individual", "150.00"),
    ("Ecografía de abdomen completo y transvaginal", "230.00"),
    ("Ecografía de abdomen completo y próstata", "220.00"),
))

ECOGRAFIA_DOPPLER = Tariff("DOP", ServiceKind.IMAGENES, "Ecografía", 40, (
    ("Doppler arterial de miembro inferior", "193.00"),
    ("Doppler arterial de miembro superior", "143.00"),
    ("Doppler venoso de miembro inferior", "193.00"),
    ("Doppler venoso de miembro superior", "143.00"),
    ("Doppler de testículo o tiroides", "150.00"),
    ("Doppler ginecológico, transvaginal, renal o prostático", "200.00"),
    ("Doppler obstétrico", "200.00"),
))

TOPICO = Tariff("TOP", ServiceKind.PROCEDIMIENTO, "Enfermería / Tópico", 20, (
    ("Curación simple", "45.00"),
    ("Curación mediana", "60.00"),
    ("Curación grande", "90.00"),
    ("Curación múltiple", "105.00"),
    ("Curación infectada", "120.00"),
    ("Curación de pie diabético", "120.00"),
    ("Curación de ombligo", "36.00"),
    ("Curación de quemadura pequeña", "60.00"),
    ("Curación de quemadura mediana", "90.00"),
    ("Curación de quemadura de tercer grado", "150.00"),
    ("Curación de úlcera", "60.00"),
    ("Curación de escara de primer grado", "70.00"),
    ("Curación de escara de segundo grado", "80.00"),
    ("Curación de escara de tercer grado", "90.00"),
    ("Curación vaginal", "120.00"),
    ("Curación de oído unilateral", "60.00"),
    ("Curación de oído bilateral", "100.00"),
    ("Curación ocular unilateral", "110.00"),
    ("Lavado de oído unilateral", "30.00"),
    ("Lavado de oído bilateral", "60.00"),
    ("Lavado ocular", "60.00"),
    ("Lavado ocular bilateral", "80.00"),
    ("Lavado gástrico", "150.00"),
    ("Nebulización de una sesión", "30.00"),
    ("Nebulización con equipo, sesión de tres veces", "60.00"),
    ("Nebulización con oxígeno", "75.00"),
    ("Colocación de sonda Foley", "60.00"),
    ("Retiro de sonda Foley", "30.00"),
    ("Colocación de sonda nasogástrica", "60.00"),
    ("Cambio de sonda nasogástrica o vesical", "75.00"),
    ("Cateterismo vesical", "75.00"),
    ("Aspiración vesical", "60.00"),
    ("Aspiración de secreciones", "60.00"),
    ("Colocación de enema", "50.00"),
    ("Estimulación rectal", "15.00"),
    ("Colocación de bolsa colectora", "45.00"),
    ("Cambio de dispositivo de colostomía", "75.00"),
    ("Control de glucosa capilar", "12.00"),
    ("Glucosa capilar por emergencia", "15.00"),
    ("Pauta de insulinización sin medicamentos", "120.00"),
    ("Medios físicos", "15.00"),
    ("Retiro de puntos hasta cuatro", "39.00"),
    ("Retiro de puntos de cinco a nueve", "45.00"),
    ("Retiro de puntos de diez a más", "60.00"),
    ("Retiro de puntos de ginecología", "60.00"),
    ("Retiro de tapones nasales", "45.00"),
    ("Perforación de lóbulo de la oreja", "45.00"),
    ("Ablación de uña parcial", "60.00"),
    ("Ablación de uña total", "75.00"),
))

CIRUGIA_MENOR = Tariff("PRC", ServiceKind.PROCEDIMIENTO, "Cirugía General", 45, (
    ("Sutura de primer plano hasta dos puntos", "75.00"),
    ("Sutura de primer plano de tres a cinco puntos", "90.00"),
    ("Sutura de primer plano de seis a diez puntos", "120.00"),
    ("Sutura de primer plano de once a quince puntos", "120.00"),
    ("Sutura de primer plano de dieciséis puntos a más", "150.00"),
    ("Sutura de segundo plano menor o igual a diez centímetros", "180.00"),
    ("Sutura de segundo plano mayor a diez centímetros", "210.00"),
    ("Sutura de tercer plano hasta quince puntos", "240.00"),
    ("Sutura de tercer plano de dieciséis puntos a más", "270.00"),
    ("Sutura de cara", "120.00"),
    ("Sutura de desgarro vaginal", "180.00"),
    ("Cierre de herida por tercera intención", "240.00"),
    ("Incisión y drenaje de absceso", "75.00"),
    ("Drenaje de absceso pequeño menor de tres centímetros", "90.00"),
    ("Drenaje de absceso mediano de tres a seis centímetros", "150.00"),
    ("Drenaje de absceso grande mayor de seis centímetros", "210.00"),
    ("Drenaje de absceso de dedo", "90.00"),
    ("Drenaje de absceso en cara", "180.00"),
    ("Drenaje de absceso en cuello", "180.00"),
    ("Drenaje de absceso mamario", "180.00"),
    ("Drenaje de absceso profundo subaponeurótico", "150.00"),
    ("Drenaje de quiste sebáceo infectado", "210.00"),
    ("Drenaje articular", "180.00"),
    ("Drenaje de hematoma o absceso nasal", "90.00"),
    ("Debridación de absceso mediano", "120.00"),
    ("Debridación de absceso grande", "150.00"),
    ("Debridación de absceso de Bartholino", "150.00"),
    ("Debridación de piel infectada extensa", "180.00"),
    ("Limpieza quirúrgica pequeña", "130.00"),
    ("Limpieza quirúrgica mediana", "180.00"),
    ("Limpieza quirúrgica grande", "230.00"),
    ("Biopsia incisional de piel", "160.00"),
    ("Biopsia excisional completa de piel", "160.00"),
    ("Extracción de lunar pequeño menor de cinco milímetros", "130.00"),
    ("Extracción de lunar mediano de cinco a diez milímetros", "180.00"),
    ("Extracción de lunar grande mayor de diez milímetros", "230.00"),
    ("Extracción de lipoma pequeño menor de dos centímetros", "180.00"),
    ("Extracción de lipoma mediano de dos a cinco centímetros", "280.00"),
    ("Extracción de lipoma grande mayor de cinco centímetros", "380.00"),
    ("Extracción de lipoma con monitoreo ecográfico", "240.00"),
    ("Extracción de quiste epidérmico pequeño", "180.00"),
    ("Extracción de quiste epidérmico mediano", "280.00"),
    ("Extracción de quiste epidérmico grande", "380.00"),
    ("Extracción de tumor de partes blandas menor a tres centímetros", "180.00"),
    ("Extracción de tumor de partes blandas mayor a tres centímetros", "300.00"),
    ("Extracción de tumor de partes blandas mayor a siete centímetros", "390.00"),
    ("Extracción de ganglión", "120.00"),
    ("Extracción de cuerpo extraño superficial", "180.00"),
    ("Extracción de cuerpo extraño profundo", "290.00"),
    ("Extracción de cuerpo extraño en conducto auditivo externo", "90.00"),
    ("Extracción de cuerpo extraño intranasal", "120.00"),
    ("Extracción de cuerpo extraño en faringe", "150.00"),
    ("Extracción de cuerpo extraño en ojo", "90.00"),
    ("Extracción de larvas", "90.00"),
    ("Extracción de hiperqueratosis", "90.00"),
    ("Cauterización de verruga única", "120.00"),
    ("Cauterización de verrugas de dos a cuatro", "180.00"),
    ("Cauterización de verrugas múltiples", "240.00"),
    ("Cauterización de verrugas genitales", "240.00"),
    ("Cauterización química con podofilina por sesión", "45.00"),
    ("Electrocauterización dérmica", "120.00"),
    ("Cauterización o taponamiento nasal", "60.00"),
    ("Fijación de fractura nasal", "90.00"),
    ("Infiltración intraarticular", "180.00"),
    ("Infiltración muscular o tendinosa", "180.00"),
    ("Infiltración de partes blandas", "210.00"),
    ("Infiltración de cicatriz queloide", "120.00"),
    ("Infiltración de cicatriz queloide en áreas extensas", "210.00"),
    ("Retiro de queloide por sesión", "400.00"),
    ("Artrocentesis", "240.00"),
    ("Paracentesis", "300.00"),
    ("Paracentesis evacuadora y diagnóstica", "360.00"),
    ("Toracocentesis", "150.00"),
    ("Escisión de hemorroide trombosada", "240.00"),
    ("Trombectomía hemorroidal", "330.00"),
    ("Anoscopía", "60.00"),
    ("Aspiración de absceso pequeño", "90.00"),
    ("Aspiración de absceso mediano", "120.00"),
    ("Aspiración de absceso grande", "240.00"),
    ("Aspiración de quiste de mama", "180.00"),
    ("Aspiración de quiste de mama con guía ecográfica", "270.00"),
    ("Aspiración de oído unilateral", "240.00"),
    ("Corrección de pabellón auricular", "195.00"),
    ("Debridación de hematoma auricular", "90.00"),
))

TRAUMATOLOGIA = Tariff("TRA", ServiceKind.PROCEDIMIENTO, "Traumatología", 40, (
    ("Colocación de yeso corto de brazo o pierna", "105.00"),
    ("Colocación de yeso mediano", "120.00"),
    ("Colocación de yeso grande", "180.00"),
    ("Colocación de yeso de mano a antebrazo", "120.00"),
    ("Colocación de yeso de hombro a mano", "135.00"),
    ("Colocación de yeso largo para la pierna", "150.00"),
    ("Colocación de yeso muslopedio", "180.00"),
    ("Colocación de yeso rotuliano con soporte de tendón", "150.00"),
    ("Colocación de yeso en espica de cadera", "105.00"),
    ("Colocación de yeso corporal de hombro a caderas", "150.00"),
    ("Colocación de yeso en ocho o vendaje acromioclavicular", "150.00"),
    ("Colocación de yeso para nariz o collarín", "120.00"),
    ("Colocación de yeso de contacto total rígido de pierna", "120.00"),
    ("Colocación de yeso para pie zambo", "150.00"),
    ("Retiro de yeso pequeño", "45.00"),
    ("Retiro de yeso mediano", "45.00"),
    ("Retiro de yeso grande", "60.00"),
    ("Retiro de yeso nasal", "60.00"),
    ("Férula digital", "60.00"),
    ("Férula corta de brazo o pierna", "90.00"),
    ("Férula mediana", "105.00"),
    ("Férula larga de brazo o pierna", "120.00"),
    ("Férula de yeso con vendaje elástico", "120.00"),
    ("Colocación de corsé", "90.00"),
    ("Colocación de vendaje elástico costal", "30.00"),
    ("Tratamiento cerrado de luxación de hombro", "180.00"),
    ("Tratamiento cerrado de luxación de codo o muñeca", "180.00"),
    ("Tratamiento cerrado de luxación de rodilla", "180.00"),
    ("Tratamiento cerrado de luxación de cadera, rodilla o tobillo", "360.00"),
    ("Tratamiento cerrado de luxación de tobillo", "210.00"),
    ("Tratamiento cerrado de luxación rotuliana", "210.00"),
    ("Tratamiento cerrado de subluxación de cabeza de radio en niños", "90.00"),
    ("Tratamiento cerrado de fractura de falange", "90.00"),
    ("Tratamiento cerrado de fractura metacarpiana", "90.00"),
    ("Tratamiento cerrado de fractura de escafoides", "144.00"),
    ("Tratamiento cerrado de fractura de cúbito o radio", "180.00"),
    ("Tratamiento cerrado de fractura de cabeza o cuello de radio", "180.00"),
    ("Tratamiento cerrado de fractura de diáfisis del húmero", "240.00"),
    ("Tratamiento cerrado de fractura de húmero proximal", "180.00"),
    ("Tratamiento cerrado de fractura de clavícula", "180.00"),
    ("Tratamiento cerrado de fractura escapular", "120.00"),
    ("Tratamiento cerrado de fractura tibial", "120.00"),
    ("Tratamiento cerrado de fractura de diáfisis tibial", "450.00"),
    ("Tratamiento cerrado de fractura de peroné distal", "270.00"),
    ("Tratamiento cerrado de fractura de maléolo medial", "270.00"),
    ("Tratamiento cerrado de fractura bimaleolar de tobillo", "270.00"),
    ("Tratamiento cerrado de fractura trimaleolar de tobillo", "90.00"),
    ("Tratamiento cerrado de fractura de calcáneo o astrágalo", "240.00"),
    ("Tratamiento cerrado de fractura rotuliana sin manipulación", "120.00"),
    ("Tratamiento cerrado de fractura de diáfisis femoral", "600.00"),
    ("Tratamiento cerrado de fractura de extremo femoral", "300.00"),
    ("Tratamiento cerrado de fractura de acetábulo", "300.00"),
    ("Tratamiento cerrado de fractura coccígea", "150.00"),
    ("Tratamiento abierto de fractura de hueso nasal", "270.00"),
))

APOYO_DIAGNOSTICO = Tariff("DXA", ServiceKind.PROCEDIMIENTO, None, 30, (
    ("Electrocardiograma en el centro médico", "63.00"),
    ("Electrocardiograma a domicilio", "90.00"),
    ("Espirometría", "90.00"),
    ("Espirometría de control", "30.00"),
    ("Audiometría", "90.00"),
    ("Audiometría de tonos puros por vía aérea y ósea", "120.00"),
))

OPTOMETRIA = Tariff("OPT", ServiceKind.PROCEDIMIENTO, "Optometría", 20, (
    ("Evaluación optométrica", "90.00"),
    ("Test de Ishihara", "75.00"),
    ("Test de la mosca (estereopsis)", "75.00"),
    ("Test de Schirmer", "75.00"),
    ("Campimetría uni o bilateral", "75.00"),
    ("Sondaje y lavado de vías lagrimales", "60.00"),
))

GINECO_OBSTETRICIA = Tariff("OBS", ServiceKind.PROCEDIMIENTO, "Obstetricia", 40, (
    ("Inserción de DIU", "180.00"),
    ("Retiro de DIU normal", "120.00"),
    ("Retiro de DIU incrustado", "150.00"),
    ("Retiro de implante subdérmico", "105.00"),
    ("Sesión de psicoprofilaxis obstétrica", "60.00"),
    ("Marsupialización de glándula de Bartholino", "300.00"),
    ("Atención de parto vaginal con atención posparto", "3450.00"),
))

PAQUETES = Tariff("PAQ", ServiceKind.OTRO, "Obstetricia", 30, (
    ("Paquete de atención de gestante desde el primer o segundo trimestre", "3600.00"),
    ("Paquete de atención de gestante desde el tercer trimestre", "2900.00"),
    ("Paquete de atención de gestante con parto inminente", "2200.00"),
))

TERAPIA_FISICA = Tariff("TER", ServiceKind.PROCEDIMIENTO, "Terapia Física y Rehabilitación", 45, (
    ("Sesión de terapia física y rehabilitación", "30.00"),
    ("Paquete de seis sesiones de terapia física", "170.00"),
    ("Paquete de diez sesiones de terapia física", "280.00"),
    ("Masaje relajante de 45 minutos", "30.00"),
    ("Masaje descontracturante con terapia física", "30.00"),
    ("Magnetoterapia de 30 minutos", "50.00"),
    ("Compresas frías", "15.00"),
    ("Terapia del lenguaje individual", "75.00"),
    ("Terapia del habla individual", "90.00"),
    ("Terapia del habla grupal por persona", "60.00"),
    ("Terapia de aprendizaje", "90.00"),
))

PSICOLOGIA = Tariff("PSI", ServiceKind.CONSULTA, "Psicología", 45, (
    ("Informe psicológico", "90.00"),
    ("Evaluación conductual en niños (una sesión)", "80.00"),
    ("Modificación de conducta en niños (cuatro sesiones)", "160.00"),
    ("Evaluación psicológica integral de niños y adolescentes (dos sesiones)", "140.00"),
    ("Evaluación de problemas de aprendizaje (una sesión)", "80.00"),
    ("Orientación vocacional (dos sesiones)", "80.00"),
    ("Psicoterapia de pareja (una sesión)", "60.00"),
    ("Psicoterapia de pareja (cuatro sesiones)", "200.00"),
    ("Psicoterapia familiar (una sesión)", "70.00"),
    ("Psicoterapia familiar (cuatro sesiones)", "240.00"),
    ("Psicoterapia en niños (de dos a cuatro sesiones, desde)", "100.00"),
    ("Psicoterapia en adolescentes (de cuatro a seis sesiones, desde)", "200.00"),
    ("Psicoterapia en adultos (de seis a ocho sesiones, desde)", "300.00"),
    ("Psicología geriátrica (una sesión)", "60.00"),
    ("Test de inteligencia", "60.00"),
    ("Test de personalidad", "60.00"),
    ("Test vocacional", "60.00"),
))

ODONTOLOGIA = Tariff("ODO", ServiceKind.PROCEDIMIENTO, "Odontología", 45, (
    ("Profilaxis dental", "80.00"),
    ("Destartraje y profilaxis", "120.00"),
    ("Curación dental", "40.00"),
    ("Obturación con resina simple", "120.00"),
    ("Obturación con resina compleja", "180.00"),
    ("Exodoncia simple", "80.00"),
    ("Exodoncia complicada", "150.00"),
    ("Blanqueamiento dental en consultorio", "600.00"),
    ("Extracción de muela del juicio simple", "180.00"),
    ("Extracción de muela del juicio semirretenida", "300.00"),
    ("Extracción de muela del juicio retenida compleja", "500.00"),
    ("Extracción de canino retenido", "700.00"),
    ("Cirugía bucal avanzada", "900.00"),
    ("Exéresis de quiste maxilar pequeño", "900.00"),
    ("Exéresis de quiste maxilar complejo", "1800.00"),
    ("Exéresis de tumor maxilar benigno", "2800.00"),
    ("Exéresis de mucocele", "500.00"),
    ("Exéresis de ránula simple", "1000.00"),
    ("Submaxilectomía", "4000.00"),
    ("Parotidectomía superficial", "5500.00"),
    ("Artrocentesis de articulación temporomandibular", "1500.00"),
    ("Cirugía abierta de articulación temporomandibular", "6500.00"),
    ("Cierre de fístula oroantral", "1000.00"),
    ("Cierre de comunicación bucosinusal", "1500.00"),
    ("Tratamiento quirúrgico de sinusitis odontogénica", "2200.00"),
    ("Exéresis de torus o exóstosis", "700.00"),
    ("Reducción de tuberosidad maxilar agrandada", "1000.00"),
    ("Regularización ósea posextracción", "500.00"),
    ("Frenectomía labial", "450.00"),
    ("Frenectomía lingual", "600.00"),
    ("Corrección de cicatrices faciales", "1000.00"),
    ("Tratamiento del dolor facial", "2200.00"),
))

ESTETICA = Tariff("EST", ServiceKind.PROCEDIMIENTO, "Medicina Estética", 45, (
    ("Toxina botulínica en entrecejo", "700.00"),
    ("Toxina botulínica en frente", "600.00"),
    ("Toxina botulínica en patas de gallo", "600.00"),
    ("Elevación de cejas", "350.00"),
    ("Corrección de sonrisa gingival", "250.00"),
    ("Toxina botulínica en comisuras labiales", "250.00"),
    ("Tratamiento de bruxismo y tensión mandibular", "1800.00"),
    ("Tratamiento estético de cuello", "1300.00"),
    ("Toxina botulínica facial completa", "750.00"),
    ("Toxina botulínica facial en varones", "650.00"),
    ("Tratamiento de hiperhidrosis axilar", "900.00"),
    ("Limpieza facial profunda con vitaminas", "250.00"),
    ("Plasma rico en plaquetas facial", "120.00"),
    ("Tratamiento de la caída del cabello", "100.00"),
    ("Tratamiento de ojeras por sesión", "100.00"),
    ("Cauterización de lunares", "150.00"),
    ("Eliminación de acrocordones", "75.00"),
    ("Infiltración de queloides", "130.00"),
))

AMBULANCIA = Tariff("AMB", ServiceKind.OTRO, None, 120, (
    ("Traslado en ambulancia dentro de la ciudad", "100.00"),
    ("Traslado en ambulancia al hospital de Satipo", "70.00"),
    ("Traslado en ambulancia a La Campiña", "350.00"),
    ("Traslado en ambulancia a Mazamari", "230.00"),
    ("Traslado en ambulancia a Pangoa", "450.00"),
    ("Traslado en ambulancia a Pichanaqui", "450.00"),
    ("Traslado en ambulancia a La Merced", "900.00"),
    ("Traslado en ambulancia a Tarma", "1700.00"),
    ("Traslado en ambulancia a La Oroya", "2500.00"),
    ("Traslado en ambulancia a Huancayo", "2500.00"),
    ("Traslado en ambulancia a Lima", "3500.00"),
    ("Traslado en ambulancia a Tarma con médico", "2200.00"),
    ("Traslado en ambulancia a La Oroya con médico", "2700.00"),
    ("Traslado en ambulancia a Huancayo con médico", "2700.00"),
    ("Traslado en ambulancia a Lima con médico", "3700.00"),
))

TARIFF: tuple[Tariff, ...] = (
    CONSULTAS,
    CONSULTAS_ESPECIALIDAD,
    ADMINISTRATIVOS,
    HOSPITALIZACION,
    INYECTABLES,
    VACUNAS,
    LABORATORIO,
    RAYOS_X,
    DENSITOMETRIA,
    ECOGRAFIA,
    ECOGRAFIA_DOPPLER,
    TOPICO,
    CIRUGIA_MENOR,
    TRAUMATOLOGIA,
    APOYO_DIAGNOSTICO,
    OPTOMETRIA,
    GINECO_OBSTETRICIA,
    PAQUETES,
    TERAPIA_FISICA,
    PSICOLOGIA,
    ODONTOLOGIA,
    ESTETICA,
    AMBULANCIA,
)


def seed_catalog(db: Session) -> None:
    """Crea las especialidades y los servicios del tarifario que falten."""
    specialties = _ensure_specialties(db)
    _ensure_services(db, specialties)


def _ensure_specialties(db: Session) -> dict[str, Specialty]:
    existing = {
        specialty.name: specialty
        for specialty in db.execute(select(Specialty)).scalars().all()
    }
    created = [
        Specialty(name=name, description=description, default_duration_minutes=duration)
        for name, description, duration in SPECIALTIES
        if name not in existing
    ]
    if created:
        db.add_all(created)
        db.flush()
        existing.update({specialty.name: specialty for specialty in created})
        logger.info("Especialidades cargadas: %d", len(created))
    return existing


def _ensure_services(db: Session, specialties: dict[str, Specialty]) -> None:
    """Agrega los servicios que faltan, comparando por código y por nombre.

    Se compara también por nombre porque las bases instaladas antes de este
    tarifario tienen algunos exámenes con otro código, y porque el
    administrador pudo haberlos creado a mano: en ambos casos la fila existente
    es la buena, con el precio que el establecimiento ya decidió.
    """
    taken_codes = {
        code.upper() for code in db.execute(select(MedicalService.code)).scalars().all()
    }
    taken_names = {
        _normalize(name) for name in db.execute(select(MedicalService.name)).scalars().all()
    }

    created = 0
    for block in TARIFF:
        for index, item in enumerate(block.items, start=1):
            name, price = item[0], item[1]
            code = LEGACY_CODES.get(name, f"{block.prefix}-{index:03d}")
            if code.upper() in taken_codes or _normalize(name) in taken_names:
                continue

            group = item[2] if len(item) > 2 else block.specialty
            specialty = specialties.get(group) if group else None
            db.add(
                MedicalService(
                    code=code,
                    name=name,
                    kind=block.kind.value,
                    specialty_id=specialty.id if specialty else None,
                    price=Decimal(price),
                    duration_minutes=block.duration,
                )
            )
            taken_codes.add(code.upper())
            taken_names.add(_normalize(name))
            created += 1

    if created:
        db.commit()
        logger.info("Servicios del tarifario cargados: %d", created)


def _normalize(name: str) -> str:
    return " ".join(name.split()).casefold()
