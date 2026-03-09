#!/bin/bash

make

if [ $? -eq 0 ]; then
    make program
else
    echo "Errore durante la compilazione. Impossibile caricare il programma."
fi

