# Makefile per compilare, programmare e ottenere i dati sulla memoria di un programma per l'attiny13a

# Nome del file sorgente
SOURCE = main.c

# Nome del file eseguibile generato
TARGET = main

# Microcontrollore target
MCU = attiny13

# Frequenza di clock del microcontrollore (in Hz)
F_CPU = 9600000

# Directory contenente i file di inclusione
INC_DIR =

# Directory contenente i file di libreria
LIB_DIR =

# Flags del compilatore
CFLAGS = -mmcu=$(MCU) -Os -DF_CPU=$(F_CPU)

# Comando per compilare il programma
CC = avr-gcc -Os

# Comando per copiare il programma nel microcontrollore
AVRDUDE = avrdude
AVRDUDE_PROGRAMMER = -c avrisp
AVRDUDE_MCU = -p $(MCU)
AVRDUDE_PORT = -P /dev/ttyUSB0
AVRDUDE_BAUDRATE = -b 19200
AVRDUDE_FLASH = -U flash:w:$(TARGET).hex



all: $(TARGET).hex

$(TARGET).hex: $(TARGET).elf
	avr-objcopy -O ihex $< $@

$(TARGET).elf: $(SOURCE) light_ws2812.c
	$(CC) $(CFLAGS) -o $@ $^ $(INC_DIR) $(LIB_DIR)

program: $(TARGET).hex
	$(AVRDUDE) $(AVRDUDE_PROGRAMMER) $(AVRDUDE_MCU) $(AVRDUDE_PORT) $(AVRDUDE_BAUDRATE) $(AVRDUDE_FLASH)

clean:
	rm -f $(TARGET).elf $(TARGET).hex

.PHONY: all program clean

# Regola target per compilare, programmare e ottenere i dati sulla memoria
compile_program_size: all program size

size:
	avr-size $(TARGET).elf


