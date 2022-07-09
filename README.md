# ModemSimul
This is a `serial modem simulator` to help during test and development for `GPRS connections`. Once started the software will open the `Serial port` and answer any connection in it. It will behave as a `GPRS Modem` so it will you to develop an external Hardware like Arduino, ESP32, Raspberri Pi Pico, or similar, so that hardware will be able to talk to ModemSimul as if it would be a GSM Module (`SIMCOM SIM7600 series`), once you tell ModemSimul to open a GPRS connection it will link to the `TCP Port` you configured as the first argument and it will forward connections between this `TCP Port` and your hardware connection through the `Serial connection`.

```
Usage: ./modemsimul.py <tcp port> <serial port> [serial speed [serial config]]
    > Example: {} 2222 /dev/ttyUSB0 115200
    > Default serial speed will be: 9600
    > Default serial config will be: 8N1
```
