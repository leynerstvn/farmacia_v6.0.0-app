def numero_a_letras(numero):
    indicador = [("",""),("MIL","MIL"),("MILLON","MILLONES"),("MIL","MIL"),("BILLON","BILLONES")]
    entero = int(numero)
    decimal = int(round((numero - entero)*100))
    if entero == 0:
        return f"CERO CON {decimal:02d}/100"

    contador = 0
    numero_letras = ""
    while entero > 0:
        a = entero % 1000
        if contador == 0:
            en_letras = convierte_cifra(a, 1).strip()
        else:
            en_letras = convierte_cifra(a, 0).strip()
        if a == 0:
            numero_letras = en_letras + " " + numero_letras
        elif a == 1:
            if contador in (1,3):
                numero_letras = indicador[contador][0] + " " + numero_letras
            else:
                numero_letras = en_letras + " " + indicador[contador][0] + " " + numero_letras
        else:
            numero_letras = en_letras + " " + indicador[contador][1] + " " + numero_letras
        numero_letras = numero_letras.strip()
        contador = contador + 1
        entero = int(entero / 1000)
    return numero_letras + f" CON {decimal:02d}/100"

def convierte_cifra(numero, sw):
    lista_centana = ["",("CIEN","CIENTO"),"DOSCIENTOS","TRESCIENTOS","CUATROCIENTOS","QUINIENTOS","SEISCIENTOS","SETECIENTOS","OCHOCIENTOS","NOVECIENTOS"]
    lista_decena = ["",("DIEZ","ONCE","DOCE","TRECE","CATORCE","QUINCE","DIECISEIS","DIECISIETE","DIECIOCHO","DIECINUEVE"),
                    ("VEINTE","VEINTI"),("TREINTA","TREINTA Y "),("CUARENTA" , "CUARENTA Y "),
                    ("CINCUENTA" , "CINCUENTA Y "),("SESENTA" , "SESENTA Y "),
                    ("SETENTA" , "SETENTA Y "),("OCHENTA" , "OCHENTA Y "),
                    ("NOVENTA" , "NOVENTA Y ")
                ]
    lista_unidad = ["",("UN" , "UNO"),"DOS","TRES","CUATRO","CINCO","SEIS","SIETE","OCHO","NUEVE"]
    centena = int(numero / 100)
    decena = int((numero -(centena * 100))/10)
    unidad = int(numero - (centena * 100 + decena * 10))

    texto_centena = ""
    texto_decena = ""
    texto_unidad = ""

    # Centena
    if centena == 1:
        if decena == 0 and unidad == 0:
            texto_centena = lista_centana[1][0]
        else:
            texto_centena = lista_centana[1][1]
    else:
        texto_centena = lista_centana[centena]

    # Decena
    if decena == 1:
        texto_decena = lista_decena[1][unidad]
    elif decena > 1:
        if unidad == 0:
            texto_decena = lista_decena[decena][0]
        else:
            texto_decena = lista_decena[decena][1]
    
    # Unidad
    if decena != 1:
        if unidad == 1:
            if sw == 1:
                texto_unidad = lista_unidad[1][1]
            else:
                texto_unidad = lista_unidad[1][0]
        else:
            texto_unidad = lista_unidad[unidad]

    return f"{texto_centena} {texto_decena}{texto_unidad}"
