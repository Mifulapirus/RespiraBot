#!/usr/bin/env python
""" Bot conversacional para la recogida de datos.
RespiraBot es un bot para ayudar a organizar la logística durante la fabricación masiva de Viseras y Equipos de Protección Individual requeridos durante el comienzo de la Pandema de Coronavirus de 2020.
Este bot está basado en el ejemplo de bot conversacional de Telegram: # https://github.com/python-telegram-bot/python-telegram-bot/blob/master/examples/conversationbot.py

Instalación de prerequisitos:
    pip3 install gspread oauth2client emoji python-telegram-bot --upgrade
"""

import logging
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, Handler)
import os.path
import sys
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import emoji
from configparser import SafeConfigParser
from datetime import datetime
import random

__author__ = "Angel Hernandez"
__credits__ = ["Angel Hernandez", "Joseba Egia"]
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = "Angel Hernandez"
__email__ = "angel@gaubit.com
__status__ = "Production"

# Pasos de la conversación: Cada uno de estos pasos va enumerado para la posterior identificacion de la etapa en la que se encuentre la conversación.
CONFIRMACION_ENTREGA, CONFIRMAR_PROGRAMAR, CANTIDAD_OSAKIDETZA, 
    MODELO_ANTERIOR, RECEPCION_PLA, BOBINAS_ENTREGADAS, 
    CANTIDAD_BOBINAS_ENTREGADAS, NO_ENTREGADO, PROVINCIA, DIAMETRO_PLA, 
    CANTIDAD_OSAKIDETZA_PREPARADA, CANTIDAD_ANTERIOR_PREPARADA, MUNICIPIO, 
    DIRECCION, HORARIO, TELEFONO = range(16)

# Paths por defecto
ownName = os.path.basename(__file__)
ownPath = sys.argv[0].replace('/' + ownName, '')
logsPath = ownPath + "//logs"
ownLogPath = logsPath + "//respirabot.log"
clientSecretPath = ownPath + "//client_secret.json"
configurationPath = ownPath + "//respirabot.ini"

# Lee la configuracion del archivo respirabot.ini
config = SafeConfigParser()
config.read(configurationPath, "utf8")

# Set up del logger a un archivo y en el terminal
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

fh = logging.FileHandler(ownLogPath) #TODO Make sure this folder exists before doing this
fh.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(funcName)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)

logger.addHandler(fh)
logger.addHandler(ch)

def start(update, context):
    """ Presentacion del Bot y primera pregunta 
        - Respuesta Esperada: Álava / Bizkaia / Gipuzkoa
        - Siguiente paso: Confirmación de entrega    
    """
    user = update.message.from_user
    context.user_data['fecha_inicio'] = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
    context.user_data['nombre'] = user.first_name
    context.user_data['apellido'] = user.last_name
    context.user_data['user_id'] = user.id
    context.user_data['user_name'] = user.username
    
    logger.info("Conversación iniciada con %s", user.first_name)

    reply_keyboard = [["Álava", "Bizkaia", "Gipuzkoa"]]
    update.message.reply_text(emoji.emojize("Hola, " + update.message.from_user.first_name + 
            " soy RespiraBot 💨 y estoy aquí para ayudarte a ser más eficiente con los envíos y el material que estamos recogiendo para combatir el 🦠" +
            "\n Dime en qué provincia estás, por favor."),
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

    return PROVINCIA

def provincia(update, context):
    """ Guarda la información de la provincia de este usuario 
        - Respuesta Esperada: Si/No
        - Siguiente paso: Confirmación de entrega    
    """
    user = update.message.from_user
    context.user_data['provincia'] = update.message.text

    logger.info("%s es de %s", user.first_name, update.message.text)

    reply_keyboard = [['Confirmar recogida', 'Programar recogida']]
    update.message.reply_text(emoji.emojize("\n ¿En que te puedo ayudar?"), 
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    
    return CONFIRMAR_PROGRAMAR

def ConfirmarProgramar(update, context):
    """ Va a la rama de confirmar o Programar 
        - Respuesta Esperada: Confirmar/Programar
        - Siguiente paso: Confirmación de entrega / Programar Recogida    
    """
    user = update.message.from_user
    context.user_data['confirmar_programar'] = update.message.text

    logger.info("%s quiere %s una entrega", user.first_name, update.message.text)

    if any(ans in update.message.text for ans in ("Programar", "programar", "programar recogida", "Programar recogida")):
        context.user_data['confirmar_programar'] = "Programar"
        update.message.reply_text(emoji.emojize("\n 👌 Estupendo, me puedes decir cuantas viseras tienes del modelo de Osakidetza?"), 
                reply_markup=ReplyKeyboardRemove())
        return CANTIDAD_OSAKIDETZA_PREPARADA
    
    if any(ans in update.message.text for ans in ("Confirmar recogida", "confirmar recogida")):
        context.user_data['confirmar_programar'] = "Confirmar"
        reply_keyboard = [['Sí', 'No']]
        update.message.reply_text(emoji.emojize("\n ¿Puedes confirmar la entrega de productos? 🚚"), 
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return CONFIRMACION_ENTREGA
    
    noEntendi(update, context, [['Confirmar recogida', 'Programar recogida']])
    return CONFIRMAR_PROGRAMAR

def cantidadOsakidetzaPreparada(update, context):
    """ Numero de Viseras Osakidetza
        - Respuesta Esperada: Numérica
        - Siguiente paso: Viseras Modelo Anterior
    """
    user = update.message.from_user
    try:
        int(update.message.text)
        context.user_data['cantidad_osakidetza_preparada'] = update.message.text
        
        logger.info("Cantidad Lista para recoger del modelo Osakidetza de %s: %s", user.first_name, update.message.text)

        update.message.reply_text(emoji.emojize("👍 Estupendo, ¿me puedes decir cuantas tienes listas del modelo anterior?"),
                        reply_markup=ReplyKeyboardRemove())
    
        return CANTIDAD_ANTERIOR_PREPARADA

    except ValueError:
        logger.info(" User Input Error Cantidad Entregada a Osakidetza de %s no es un numero %s ", user.first_name, update.message.text)
        update.message.reply_text(emoji.emojize("👎 Por favor, introduce el número de unidades listas del modelo de Osakidetza."),
                        reply_markup=ReplyKeyboardRemove())
        return CANTIDAD_OSAKIDETZA_PREPARADA

def cantidadAnteriorPreparada(update, context):
    """ Numero de Viseras del modelo anterior listo para ser recogido
        - Respuesta Esperada: Numérica
        - Siguiente paso: Start / Direccion
    """
    user = update.message.from_user
    try:
        int(update.message.text)
        context.user_data['cantidad_anterior_preparada'] = update.message.text
        logger.info("Cantidad Lista para recoger del modelo Anterior de %s: %s", user.first_name, update.message.text)
        totalPreparado = int(context.user_data["cantidad_osakidetza_preparada"]) + int(context.user_data["cantidad_anterior_preparada"])
        update.message.reply_text(emoji.emojize("Ok, voy a necesitar algo de información para programar esta recogida.\n Dime cual es tu municipio."),
            reply_markup=ReplyKeyboardRemove())
        return MUNICIPIO
    except ValueError:
        logger.info(" User Input Error Cantidad Anterior Preparada de %s no es un numero %s ", user.first_name, update.message.text)
        update.message.reply_text(emoji.emojize("👎 Por favor, introduce el número de unidades listas del modelo de Anterior."),
                        reply_markup=ReplyKeyboardRemove())
        return CANTIDAD_ANTERIOR_PREPARADA

def municipio(update, context):
    """ municipio de la recogida
        - Respuesta Esperada: Texto
        - Siguiente paso: Horario
    """
    user = update.message.from_user
    context.user_data['municipio'] = update.message.text

    logger.info("El municipio de %s es: %s", user.first_name, update.message.text)

    update.message.reply_text(emoji.emojize("Muy bien, ahora la dirección para esta recogida."),
                        reply_markup=ReplyKeyboardRemove())

    return DIRECCION
    
def direccion(update, context):
    """ Direccion para programar la recogida
        - Respuesta Esperada: Texto
        - Siguiente paso: Horario
    """
    user = update.message.from_user
    context.user_data['direccion'] = update.message.text
    logger.info("%s es de %s", user.first_name, update.message.text)
    reply_keyboard = [['Mañana', 'Tarde', 'Todo el día']]
    update.message.reply_text(emoji.emojize("\n ¿En qué horario podemos pasar?"), 
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    
    return HORARIO

def horario(update, context):
    """ Horario para programar la recogida
        - Respuesta Esperada: Mañana/Tarde/Noche
        - Siguiente paso: Teléfono
    """
    user = update.message.from_user

    if any(ans in update.message.text for ans in ("Mañana", "Tarde", "Todo el día")):
        context.user_data['horario'] = update.message.text
        logger.info("%s quiere que se recoja por la %s", user.first_name, update.message.text)

        contact_keyboard = KeyboardButton(text="Enviar Contacto", request_contact=True)
        custom_keyboard = [[ contact_keyboard ]]
        reply_markup = ReplyKeyboardMarkup(custom_keyboard)
        update.message.reply_text(emoji.emojize("Muy bien, por último, dime tu teléfono"), 
                        reply_markup=reply_markup)
        return TELEFONO
    else:
        reply_keyboard = [['Mañana', 'Tarde', 'Todo el día']]
        update.message.reply_text(emoji.emojize("\n Perdona, no he entendido eso \n ¿En qué horario podemos pasar?"), 
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return HORARIO

def telefono(update, context):
    """ Telefono de contacto
        - Respuesta Esperada: Texto
        - Siguiente paso: Teléfono
    """
    user = update.message.from_user
    if hasattr(update.message.contact, "phone_number"):
        context.user_data['telefono'] = update.message.contact.phone_number
        logger.info("%s ha compartido su contacto: %s", user.first_name, context.user_data['telefono'])

    else:
        if len(update.message.text) < 9:
            contact_keyboard = KeyboardButton(text="Enviar Contacto", request_contact=True)
            custom_keyboard = [[ contact_keyboard ]]
            reply_markup = ReplyKeyboardMarkup(custom_keyboard)
            update.message.reply_text(emoji.emojize("\n Yo creo que ahi me faltan numeros. Dímelo de nuevo sólo con numeros (ej. 679123456) o comparte tu contacto por favor."), 
                        reply_markup=reply_markup)
            return TELEFONO

        else:
            context.user_data['telefono'] = update.message.text
            logger.info("%s ha escrito su telefono: %s", user.first_name, context.user_data['telefono'])

    update.message.reply_text(emoji.emojize("\n 👌 Genial, en la próxima recogida pasarán por tu dirección en el horario indicado. Gracias."), 
                reply_markup=ReplyKeyboardRemove())
    update.message.reply_text(emoji.emojize(config.get("mensajes", "prep_recogida")), 
                reply_markup=ReplyKeyboardRemove())

    return finConversacion(update, context)

def confirmacionEntrega(update, context):
    """ Confirmacion de entrega de modelos Osakidetza
        - Respuesta Esperada: Numérica
        - Siguiente paso: Cantidad Osakidetza o No Entregado
    """
    context.user_data['entregado_osakidetza'] = update.message.text

    user = update.message.from_user
    logger.info("Confirmación del pedido de %s: %s", user.first_name, update.message.text)

    if any(ans in update.message.text for ans in ("Sí", "Si", "si", "sí", "Bai", "bai")):
        update.message.reply_text(emoji.emojize("👌 Estupendo, ¿me puedes decir cuantos has entregado del modelo de Osakidetza?"),
                            reply_markup=ReplyKeyboardRemove())
    
        return CANTIDAD_OSAKIDETZA

    elif any(ans in update.message.text for ans in ("No", "no", "Ez", "ez")):
        reply_keyboard = [["Sí", "No"]]
        update.message.reply_text(emoji.emojize("☹️Lo sentimos, puede que nuestros compañeros de recogida hayan tenido algún problema 🚑. \n" +
        "Te pedimos que esperes un poco antes de marcar la recogida como fallida. " +
        "Si ya llevas un rato esperando o son más de las 20:00 marca la recogida como fallida para que lo tengamos en cuenta. \n ¿Prefieres esperar un rato?"),
                            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return NO_ENTREGADO
    
    else:
        noEntendi(update, context, [['Sí', 'No']])
        return CONFIRMACION_ENTREGA

def noEntregado(update, context):
    """ Material no Entregado
        - Respuesta Esperada: Recogida Fallida / Esperar
        - Siguiente Paso: Recogida Fallida / Fin Conversación
    """

    user = update.message.from_user
    logger.info("%s no ha podido entregar y dice que %s pude esperar", user.first_name, update.message.text)
    
    if any(ans in update.message.text for ans in ("No", "no", "Ez", "ez")):
        update.message.reply_text(emoji.emojize("🤷🏻‍♀️‍ Ahora mismo no sé lo que ha podido pasar. Déjame que pase esta información y el equipo tratará de solucionarlo lo antes posible. Sentimos las molestias."),
                            reply_markup=ReplyKeyboardRemove())
        
        appendToSheet(context.user_data)
        return finConversacion(update, context)
    
    elif any(ans in update.message.text for ans in ("No", "no", "Ez", "ez")):
        update.message.reply_text(emoji.emojize('Vale, gracias por tu paciencia!'),
                            reply_markup=ReplyKeyboardRemove())
        return finConversacion(update, context)
    
    else:
        noEntendi(update, context, [['Sí', 'No']])
        return NO_ENTREGADO

def cantidadOsakidetza(update, context):
    """ Numero de modelos Osakidetza entregados
        - Respuesta Esperada: Numérica
        - Siguiente paso: Modelo Anterior
    """
    user = update.message.from_user
    try:
        int(update.message.text)
        context.user_data['cantidad_osakidetza'] = update.message.text
        
        logger.info("Cantidad Entregada a Osakidetza de %s: %s", user.first_name, update.message.text)

        update.message.reply_text(emoji.emojize("👍 Estupendo, ¿me puedes decir cuantos has entregado del modelo anterior?"),
                        reply_markup=ReplyKeyboardRemove())
    
        return MODELO_ANTERIOR

    except ValueError:
        logger.info(" User Input Error Cantidad Entregada a Osakidetza de %s no es un numero %s ", user.first_name, update.message.text)
        update.message.reply_text(emoji.emojize("👎 Por favor, introduce el número de unidades del modelo de Osakidetza."),
                        reply_markup=ReplyKeyboardRemove())
        return CANTIDAD_OSAKIDETZA

def modeloAnterior(update, context):
    """ Modelo entregado anteriormente
        - Respuesta Esperada: Texto
        - Siguiente paso: Recepción de PLA
    """
    user = update.message.from_user
    try:
        int(update.message.text)
        context.user_data['modelo_anterior'] = update.message.text
        user = update.message.from_user
        logger.info("Modelo Anterior de %s: %s", user.first_name, update.message.text)
        reply_keyboard = [['Sí', 'No']]
        update.message.reply_text(emoji.emojize('Vale. \n ¿Has entregado ya bobinas vacías para su reutilización?'),
                            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return BOBINAS_ENTREGADAS

    except ValueError:
        logger.info(" User Input Error Cantidad Entregada del modelo anterior %s no es un numero %s ", user.first_name, update.message.text)
        update.message.reply_text(emoji.emojize("👎 Por favor, introduce el número de unidades del modelo anterior."),
                        reply_markup=ReplyKeyboardRemove())
        return MODELO_ANTERIOR

def recepcionPLA(update, context):
    """ Confirmación de la recepción del PLA correspondiente
        - Respuesta Esperada: Si/No
        - Siguiente paso: Cantidad PLA recibido/ Reutilización Bobinas
    """
    context.user_data['recepcion_pla'] = update.message.text
    user = update.message.from_user
    logger.info("Recepción de PLA de %s: %s", user.first_name, update.message.text)
    
    if any(ans in update.message.text for ans in ("Sí", "Si", "si", "sí", "Bai", "bai")):
        reply_keyboard = [['1.75mm', '3mm']]
        update.message.reply_text(emoji.emojize('¿De qué diámetro lo necesitas?'),
                                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return DIAMETRO_PLA
    
    elif any(ans in update.message.text for ans in ("No", "no", "Ez", "ez")):
        # reply_keyboard = [['Sí', 'No']]
        # update.message.reply_text(emoji.emojize('Vale. \n ¿Has entregado ya bobinas vacías para su reutilización?'),
        #                     reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return finConversacion(update, context)

    else:
        noEntendi(update, context, [['Sí', 'No']])
        return RECEPCION_PLA

def diametroPLA(update, context):
    """ Diámetro de PLA necesario
        - Respuesta Esperada: "1.75mm", "3mm", "Ambas"
        - Siguiente paso: Recepción de PLA
    """
    user = update.message.from_user
    logger.info("%s quiere bobinas de %s", user.first_name, update.message.text)
    
    if any(ans in update.message.text for ans in ("1.75mm", "1.75 mm", "1.75", "1,75", "175", "1")):
        context.user_data['diametro'] = "1.75"
        update.message.reply_text(emoji.emojize("1.75mm 🧵, entendido. Ya sabes lo que dicen... \n " +
                                "Más vale pequeña y juguetona que grande y torpe 😏"),
                                reply_markup=ReplyKeyboardRemove())
        return finConversacion(update, context)
    
    if any(ans in update.message.text for ans in ("3mm", "3 mm", "3")):
        context.user_data['diametro'] = "3"
        update.message.reply_text(emoji.emojize("3mm 🧶, entendido. ¡Eso! \n " +
                                "🐴 grande ande, o no ande. \n"),
                                reply_markup=ReplyKeyboardRemove())
        return finConversacion(update, context)

    else:
        logger.info("%s quiere bobinas de %s y no entiendo lo que quiere decir", user.first_name, update.message.text)
        context.user_data['diametro'] = "Err"
        noEntendi(update, context, [['1.75mm', '3mm']])
        return DIAMETRO_PLA        

def bobinasEntregadas(update, context):
    """ Confirmación de entrega de Bobinas para reutilizar
        - Respuesta Esperada: Si/No
        - Siguiente paso: Numero de bobinas / Fin
    """
    context.user_data['bobinas_entregadas'] = update.message.text
    user = update.message.from_user
    logger.info("Bobinas entregadas para reutilización de %s: %s", user.first_name, update.message.text)
    
    if any(ans in update.message.text for ans in ("Sí", "Si", "si", "sí", "Bai", "bai")):
        update.message.reply_text(emoji.emojize("¿Cuántas?"),
                           reply_markup=ReplyKeyboardRemove())
        return CANTIDAD_BOBINAS_ENTREGADAS
    
    elif any(ans in update.message.text for ans in ("No", "no", "Ez", "ez")):
        reply_keyboard = [['Sí', 'No']]
        update.message.reply_text(emoji.emojize('Muy bien. ¿Necesitas más PLA🎁?'),
                                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return RECEPCION_PLA
    
    else:
        noEntendi(update, context, [['Sí', 'No']])
        return BOBINAS_ENTREGADAS

def cantidadBobinasEntregadas(update, context):
    """ Cantidad de bobinas Entregadas para reutilizacion
        - Respuesta Esperada: Numérica
        - Siguiente paso: Fin
    """
    user = update.message.from_user
    try:
        int(update.message.text)
        context.user_data['cantidad_bobinas_entregadas'] = update.message.text

        user = update.message.from_user
        logger.info("Cantidad de bobinas entregadas para reutilización %s: %s", user.first_name, update.message.text)
        
        reply_keyboard = [['Sí', 'No']]
        update.message.reply_text(emoji.emojize('Muy bien. ¿Necesitas más PLA🎁?'),
                                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
        return RECEPCION_PLA

    except ValueError:
        logger.info(" User Input Error Cantidad de Bobinas Entregadas para reutilización de %s no es un numero %s ", user.first_name, update.message.text)
        update.message.reply_text(emoji.emojize("👎 Por favor, introduce el número de bobinas entregadas para su reutilización"),
                        reply_markup=ReplyKeyboardRemove())
        return CANTIDAD_BOBINAS_ENTREGADAS

def finSinSalvar(update, context):
    """ Finaliza la conversación sin guardar los datos """
    user = update.message.from_user
    reply_keyboard = [['Empezar']]
    update.message.reply_text(emoji.emojize("Esto es todo por ahora. Muchas gracias, " + user.first_name + 
                        "\n Si quieres empezar de nuevo, dale al botón o escribe /empezar", use_aliases=True),
                        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
    logger.info("Conversación con %s finalizada sin guardar los datos", user.first_name)

    return ConversationHandler.END

def finConversacion(update, context):
    """ Guarda los datos y finaliza la conversacion """
    user = update.message.from_user
    reply_keyboard = [['Empezar']]
    update.message.reply_text(emoji.emojize(":tada: :tada: :tada: Debuti. Esto es todo por ahora. Muchas gracias, " + user.first_name + 
                        "\n Si quieres empezar de nuevo, dale al botón o escribe /empezar", use_aliases=True),
                        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

    logger.info("Conversación con %s finalizada", user.first_name)

    appendToSheet(context.user_data)
    return ConversationHandler.END

def cancel(update, context):
    """ Cancela la conversacion con el usuario
        Por el momento este método no es accesible, aunque se puede forzar enviando /cancel
    """
    user = update.message.from_user
    logger.info("%s ha cancelado la conversación.", user.first_name)
    update.message.reply_text("Bueno, pues nada... luego hablamos :(",
                              reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END

def error(update, context):
    """Captura errores provininetes del update"""
    logger.warning('Update "%s" caused error "%s"', update, context.error)
    
    reply_keyboard = [['Empezar']]

    update.message.reply_text(emoji.emojize("Perdona, algo ha ido mal mientras hablábamos. \n¿Probamos de nuevo? 👉👈 😅" + 
                        "\n Si quieres empezar de nuevo, dale al botón o escribe /empezar", use_aliases=True),
                        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

    return ConversationHandler.END

def conversationTimeout(update, context):
    user = update.message.from_user
    logger.info("La conversación con %s ha caducado.", user.first_name)

    reply_keyboard = [['Empezar']]

    update.message.reply_text(emoji.emojize("Oye, mejor hablamos luego, que ahora te veo liado. 👋" + 
                        "\n Si quieres empezar de nuevo, dale al botón o escribe /empezar", use_aliases=True),
                        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

    return ConversationHandler.END

def noEntendi(update, context, _reply_keyboard):
    """Devuelve una frase cuando no entiende la respuesta """
    primeraParte = [config.get("mensajes", "no_entendi_1_1"), 
                    config.get("mensajes", "no_entendi_1_2"), 
                    config.get("mensajes", "no_entendi_1_3")]
    segundaParte = [config.get("mensajes", "no_entendi_2_1"), 
                    config.get("mensajes", "no_entendi_2_2"), 
                    config.get("mensajes", "no_entendi_2_3")]

    random.shuffle(primeraParte)
    respuesta = primeraParte[random.randrange(2)] + update.message.from_user.first_name 
    random.shuffle(segundaParte)
    respuesta = respuesta + segundaParte[random.randrange(2)]

    user = update.message.from_user
    logger.info("%s no ha usado el boton y me ha dicho %s", user.first_name, update.message.text)
    reply_keyboard = _reply_keyboard
    update.message.reply_text(emoji.emojize(respuesta), 
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

def appendToSheet(user_data):
    """ Añade una nueva fila con los valores obtenidos 
        - Input: context.user_data
    """
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

    # Usa los credenciales del archivo que este en el path de clientSecretPath
    creds = ServiceAccountCredentials.from_json_keyfile_name(clientSecretPath, scope)
    client = gspread.authorize(creds)

    managedData = list()
    
    if "fecha_inicio" in user_data: managedData.append(user_data["fecha_inicio"])
    else: managedData.append("NA")
    managedData.append(datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    
    if "nombre" in user_data: managedData.append(user_data["nombre"])
    else: managedData.append("NA")
    if "apellido" in user_data: managedData.append(user_data["apellido"])
    else: managedData.append("NA")
    if "user_id" in user_data: managedData.append(user_data["user_id"])
    else: managedData.append("NA")
    if "user_name" in user_data:
        if user_data["user_name"]: 
            formula = "=HYPERLINK(\"https://t.me/" + user_data["user_name"]+"\", \""+ user_data["user_name"]+"\")"
            linkToUser = managedData.append(formula)
        else: managedData.append("NA")
    else: managedData.append("NA")
    if "provincia" in user_data: managedData.append(user_data["provincia"])
    else: managedData.append("NA")

    if "Confirmar" in user_data["confirmar_programar"]:
        if "entregado_osakidetza" in user_data: managedData.append(user_data["entregado_osakidetza"])
        else: managedData.append("NA")
        if "cantidad_osakidetza" in user_data: managedData.append(user_data["cantidad_osakidetza"])
        else: managedData.append("NA")
        if "modelo_anterior" in user_data: managedData.append(user_data["modelo_anterior"])
        else: managedData.append("NA")
        if "recepcion_pla" in user_data: managedData.append(user_data["recepcion_pla"])
        else: managedData.append("NA")
        if "diametro" in user_data: managedData.append(user_data["diametro"])
        else: managedData.append("NA")
        if "cantidad_pla_recibido" in user_data: managedData.append(user_data["cantidad_pla_recibido"])
        else: managedData.append("NA")
        if "bobinas_entregadas" in user_data: managedData.append(user_data["bobinas_entregadas"])
        else: managedData.append("NA")
        if "cantidad_bobinas_entregadas" in user_data: managedData.append(user_data["cantidad_bobinas_entregadas"])
        else: managedData.append("NA")

        sheetName = config.get("google", "sheet_Confirmadas")

    
    elif "Programar" in user_data["confirmar_programar"]:
        if "cantidad_osakidetza_preparada" in user_data: managedData.append(user_data["cantidad_osakidetza_preparada"])
        else: managedData.append("NA")
        if "cantidad_anterior_preparada" in user_data: managedData.append(user_data["cantidad_anterior_preparada"])
        else: managedData.append("NA")
        if "municipio" in user_data: managedData.append(user_data["municipio"])
        else: managedData.append("NA")
        if "direccion" in user_data: managedData.append(user_data["direccion"])
        else: managedData.append("NA")
        if "horario" in user_data: managedData.append(user_data["horario"])
        else: managedData.append("NA")
        if "telefono" in user_data: managedData.append(user_data["telefono"])
        else: managedData.append("NA")

        sheetName = config.get("google", "sheet_programadas")

    logger.info("Guardando datos en la hoja %s", sheetName) 
    logger.info(managedData)

    #Hoja de excel con los resultados del bot
    userDataSheet = config.get("google", "userDataSheet")
    userDataSheet_backup =  config.get("google", "userDataSheet_backup")
    #Abre la hoja con el nombre indicado por userDataSheet y añade los nuevos datos
    sheet = client.open(userDataSheet).worksheet(sheetName).append_row(managedData, value_input_option='USER_ENTERED')
    sheet = client.open(userDataSheet_backup).worksheet(sheetName).append_row(managedData, value_input_option='USER_ENTERED')


def main():
    """ Creacion del bot, handles de conversacion y polling """
    logger.info("Respirabot started ")

    if len(sys.argv)>1:
        if sys.argv[1] == "produccion":
            logger.warning("---      Ejecutando Bot de Producción       ---")
            telegramToken = config.get("telegram", "token_produccion")
        
    else:
        logger.warning("---      Ejecutando Bot de desarrollo       ---")
        telegramToken = config.get("telegram", "token_dev")

    logger.info("  - Configuration Path: %s", configurationPath)
    logger.info("  - Log Path: %s", ownLogPath)
    logger.info("  - Google API Path: %s", clientSecretPath)
    logger.info("  - Google Sheet: %s", config.get("google", "userDataSheet"))
    logger.info("  - Telegram Token: %s", telegramToken)
    timeout = int(config.get("telegram", "timeout"))
    logger.info("  - Conversation Timeout: %s", timeout)
    logger.info("Waiting for conversations")

    updater = Updater(telegramToken, use_context=True)
    dp = updater.dispatcher

    # Conversation handlers
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start), CommandHandler('empezar', start), MessageHandler(Filters.regex('^(Vamos|vamos|Empezar|empezar)$'), start)],
        states={
            CONFIRMACION_ENTREGA: [MessageHandler(Filters.text, confirmacionEntrega)],
            PROVINCIA: [MessageHandler(Filters.text, provincia)],
            CONFIRMAR_PROGRAMAR: [MessageHandler(Filters.text, ConfirmarProgramar)],
            NO_ENTREGADO: [MessageHandler(Filters.text, noEntregado)],
            CANTIDAD_OSAKIDETZA: [MessageHandler(Filters.text, cantidadOsakidetza)],
            MODELO_ANTERIOR: [MessageHandler(Filters.text, modeloAnterior)],
            RECEPCION_PLA: [MessageHandler(Filters.text, recepcionPLA)],
            DIAMETRO_PLA: [MessageHandler(Filters.text, diametroPLA)],
            BOBINAS_ENTREGADAS: [MessageHandler(Filters.text, bobinasEntregadas)],
            CANTIDAD_BOBINAS_ENTREGADAS: [MessageHandler(Filters.text, cantidadBobinasEntregadas)],

            CANTIDAD_OSAKIDETZA_PREPARADA: [MessageHandler(Filters.text, cantidadOsakidetzaPreparada)],
            CANTIDAD_ANTERIOR_PREPARADA: [MessageHandler(Filters.text, cantidadAnteriorPreparada)],
            MUNICIPIO: [MessageHandler(Filters.text, municipio)],
            DIRECCION: [MessageHandler(Filters.text, direccion)],
            HORARIO: [MessageHandler(Filters.text, horario)],
            TELEFONO: [MessageHandler(Filters.all, telefono)],

            ConversationHandler.TIMEOUT: [MessageHandler(Filters.all, conversationTimeout)]
        },
        fallbacks=[Handler(cancel, pass_update_queue=True, pass_job_queue=True, pass_user_data=True, pass_chat_data=True)],
        allow_reentry=True,
        conversation_timeout = timeout
    )

    dp.add_handler(conv_handler)    

    # log errores
    dp.add_error_handler(error)
    
    updater.start_polling()
    updater.idle()     # El bot sigue corriendo hasta que se pulse Ctrl+C

if __name__ == '__main__':
    main()
