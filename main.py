from time import sleep
import board
from pwmio import PWMOut
from analogio import AnalogIn
from digitalio import DigitalInOut, Direction
import adafruit_74hc595
import supervisor
from random import randrange, choice

pwm1 = PWMOut(board.D12, duty_cycle=0, frequency=130, variable_frequency=True)
pwm2 = PWMOut(board.D11, duty_cycle=0, frequency=130, variable_frequency=True)

tune_pot = AnalogIn(board.A0)
detune_pot = AnalogIn(board.A1)
keybed_in = AnalogIn(board.A2)
tempo_pot = AnalogIn(board.A3)
pwm_2_pot = AnalogIn(board.A4)
pwm_pot = AnalogIn(board.A5)
random_pot = AnalogIn(board.D2)

random_light = DigitalInOut(board.D1)
random_light.direction = Direction.OUTPUT

pmw_2_light = DigitalInOut(board.D13)
pmw_2_light.direction = Direction.OUTPUT

pwm_2_toggle = DigitalInOut(board.D10)
pwm_2_toggle.direction = Direction.INPUT

seq_rec = DigitalInOut(board.D7)
seq_rec.direction = Direction.INPUT
seq_play_pause = DigitalInOut(board.D9)
seq_play_pause.direction = Direction.INPUT
sequence = [-1 for i in range(16)]

latch_pin = DigitalInOut(board.D5)
sr = adafruit_74hc595.ShiftRegister74HC595(board.SPI(), latch_pin)
pins = [sr.get_pin(n) for n in range(8)]
for pin in pins:
    pin.value = False

arp_run = DigitalInOut(board.SCL)
arp_run.direction = Direction.INPUT
arp_rec = DigitalInOut(board.SDA)
arp_rec.direction = Direction.INPUT
arp_light = DigitalInOut(board.D0)
arp_light.direction = Direction.OUTPUT

_TICKS_PERIOD = (1<<29)
_TICKS_MAX = (_TICKS_PERIOD-1)
_TICKS_HALFPERIOD = (_TICKS_PERIOD//2)

def ticks_diff(ticks1, ticks2):
    diff = (ticks1 - ticks2) & _TICKS_MAX
    diff = ((diff + _TICKS_HALFPERIOD) & _TICKS_MAX) - _TICKS_HALFPERIOD
    return diff

playing = False
pwm_2_on = False
bar = 0
beat = 0
keyboard_div = 4854.444  # 4681.07
arp_mode = 0
arp_on = False
last_check = supervisor.ticks_ms()
random_set = [0 for x in range(0, 16)]
arp = []
arp_step = 0
while True:
    fundamental = int(tune_pot.value / 140 + 62.5)
    detune = int(detune_pot.value / 25) - 1250
    tempo_bpm = tempo_pot.value / 220
    tempo_per_s = 60000 / tempo_bpm
    tempo_s_per_sixteenth = tempo_per_s / 4
    now = supervisor.ticks_ms()
    pins[bar].value = False
    pins[beat + 4].value = False
    if ticks_diff(now, last_check) > tempo_s_per_sixteenth:
        if len(arp) > 0:
            arp_step = ( arp_step + 1 ) % len(arp)
        if beat == 3:
            if bar == 3:
                bar = 0
                random_set = [0 for x in range(0, 16)]
            else:
                bar += 1
            beat = 0
        else:
            beat += 1
        last_check = supervisor.ticks_ms()
    if playing == True:
        pins[bar].value = True
        pins[beat + 4].value = True

    fundamental = int(tune_pot.value / 140. + 62.5)
    note = int(keybed_in.value / keyboard_div)
    f = fundamental * 2 ** (note / 12)
    f2 = fundamental * 2 ** ((note + (detune / 100)) / 12)
    pwm_ds_1 = 0
    pwm_ds_2 = 0
    if int(random_pot.value / 655) > 1 and playing == True:
        random_light.value = True
        if random_set[bar * 4 + beat] == 0:
            if randrange(1, 100) <= int(random_pot.value / 655):
                sequence[bar * 4 + beat] = randrange(-1, 13)
    else:
        random_light.value = False
    if playing == True:
        f = fundamental * 2. ** (sequence[bar * 4 + beat] / 12)
        f2 = fundamental * 2 ** ((sequence[bar * 4 + beat] + (detune / 100)) / 12)
        if sequence[bar * 4 + beat] != -1:
            pwm_ds_1 = (( pwm_pot.value / 819.1875 ) + 10) * 655
            pwm_ds_2 = (( pwm_2_pot.value / 819.1875 ) + 10) * 655
        else:
            pwm_ds_1 = 0
            pwm_ds_2 = 0
    if arp_on == True:
        sleep(0.1)
        if arp_rec.value == False:
            arp_mode = (arp_mode + 1) % 4
            arp_step = 0
            arp = list(set(arp))
            sleep(0.1)
            if arp_mode == 1:
                arp.sort()
            if arp_mode == 2:
                arp.sort(reverse = True)
            if arp_mode == 3:
                if len(arp) >= 3:
                    arp = sorted(arp) + sorted(arp, reverse=True)[1:-1]  
                else:
                    arp = sorted(arp)
            if arp_mode == 0:
                t_arp = []
                for i in range(0, len(arp) * 2):
                    t_arp.append(choice(arp))
                arp = t_arp
        note = int(keybed_in.value / keyboard_div)
        f = fundamental * 2. ** ((arp[arp_step] / 12) + note)
        f2 = fundamental * 2 ** ((arp[arp_step] + ((detune / 100)) / 12) + note)
        if arp[arp_step] != -1:
            pwm_ds_1 = (( pwm_pot.value / 819.1875 ) + 10) * 655
            pwm_ds_2 = (( pwm_2_pot.value / 819.1875 ) + 10) * 655
        else:
            pwm_ds_1 = 0
            pwm_ds_2 = 0
        if seq_rec.value == False:
            random_light.value = True
            sleep(0.1)
            t_arp = arp
            if len(arp) >= 4:
                t_arp = arp + arp + arp + arp
            sequence = t_arp[0:16]
            random_light.value = False
    if note != 0:
        f = fundamental * 2 ** (note / 12)
        f2 = fundamental * 2 ** ((note + (detune / 100)) / 12)
        pwm_ds_1 = (( pwm_pot.value / 819.1875 ) + 10) * 655
        pwm_ds_2 = (( pwm_2_pot.value / 819.1875 ) + 10) * 655
    if ticks_diff(now, last_check) > int(tempo_s_per_sixteenth * 0.9) and playing == True:
        pwm_ds_1 = 0
        pwm_ds_2 = 0
    pwm1.frequency = int(f)
    pwm1.duty_cycle = int(pwm_ds_1)
    pwm2.frequency = int(f2)
    if pwm_2_on == True:
        pwm2.duty_cycle = int(pwm_ds_2)
    else:
        pwm2.duty_cycle = 0

    if seq_rec.value == False:
        sleep(0.2)
        for bar in range(4):
            note = int(keybed_in.value / keyboard_div)
            pins[bar].value = True
            for beat in range(4):
                note = int(keybed_in.value / keyboard_div)
                pins[beat + 4].value = True
                while note == 0 and seq_play_pause.value == True:
                    note = int(keybed_in.value / keyboard_div)
                    if seq_play_pause.value == False:
                        sequence[bar * 4 + beat] = sequence[bar * 4 + beat]
                        sleep(0.1)
                        break
                    elif seq_rec.value == False:
                        sequence[bar * 4 + beat] = -1
                        sleep(0.1)
                        break
                    elif note > 0:
                        sequence[bar * 4 + beat] = note
                        sleep(0.1)
                        break
                    else:
                        sleep(0.1)
                sleep(0.1)
                pins[beat + 4].value = False
            pins[bar].value = False
    if arp_rec.value == False and arp_on == False:
        arp = []
        sleep(0.2)
        led_state = False
        note = int(keybed_in.value / keyboard_div)
        last_blink = supervisor.ticks_ms()
        while arp_rec.value == True:
            now = supervisor.ticks_ms()
            if ticks_diff(supervisor.ticks_ms(), last_blink) > 250:
                led_state = not led_state
                arp_light.value = led_state
                last_blink = supervisor.ticks_ms()
            note = int(keybed_in.value / keyboard_div)
            if note > 0:
                if len(arp) == 0:
                    arp = [note]
                elif len(arp) == 1:
                    arp.append(note)
                else:
                    arp.append(note)
                    if arp[-1] == arp[-2]:
                        arp = arp[0:-1]
                        arp[-1] = arp[-1] + 12
                sleep(0.25)
            if arp_rec.value == False:
                sleep(0.1)
                break
        arp_light.value = False
    if seq_play_pause.value == False:
        playing = not playing
        if playing == True:
            bar = 0
            beat = 0
            arp_on = False
            arp_light.value = False
        sleep(0.2)
    if pwm_2_toggle.value == False:
        pwm_2_on = not pwm_2_on
        if pwm_2_on == True:
            pmw_2_light.value = True
        else:
            pmw_2_light.value = False
        sleep(0.2)
    if arp_run.value == False and len(arp) > 0:   
        arp_on = not arp_on
        if arp_on == True:
            arp_light.value = True
            playing = False
        else:
            arp_light.value = False
        sleep(0.2) 
    random_set[bar * 4 + beat] = 1
    sleep(0.01)
