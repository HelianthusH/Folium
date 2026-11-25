EESchema Schematic File Version 4
LIBS:assembly-cache
EELAYER 29 0
EELAYER END
$Descr A4 11693 8268
encoding utf-8
Sheet 1 1
Title "VoiceCard - module assembly and wiring"
Rev "1.0"
Comp "XIAO nRF52840 Sense"
Comment1 "Net labels connect across this sheet. Panel VBUS_IN and local V5_LOCAL are isolated."
Comment2 "Module port numbers are logical. Follow the silkscreen port names on purchased modules."
$EndDescr
$Comp
L VoiceCard:USB-C_panel J1
U 1 1 67AD0000
P 1900 1500
F 0 "J1" H 1900 715 50  0000 C CNN
F 1 "USB-C_panel" H 1900 815 50  0000 C CNN
	1    1900 1500
	1    0    0    -1
$EndComp
Wire Wire Line
	450 1000 1050 1000
Text Label 450 1000 0    45   ~ 0
VBUS_IN
Wire Wire Line
	450 1100 1050 1100
Text Label 450 1100 0    45   ~ 0
USB_DP
Wire Wire Line
	450 1200 1050 1200
Text Label 450 1200 0    45   ~ 0
USB_DM
Wire Wire Line
	450 1300 1050 1300
Text Label 450 1300 0    45   ~ 0
CC1
Wire Wire Line
	450 1400 1050 1400
Text Label 450 1400 0    45   ~ 0
CC2
Wire Wire Line
	450 1500 1050 1500
Text Label 450 1500 0    45   ~ 0
GND
$Comp
L VoiceCard:BQ24074_module U1
U 1 1 67AD0001
P 5400 1500
F 0 "U1" H 5400 815 50  0000 C CNN
F 1 "BQ24074_module" H 5400 915 50  0000 C CNN
	1    5400 1500
	1    0    0    -1
$EndComp
Wire Wire Line
	3950 1100 4550 1100
Text Label 3950 1100 0    45   ~ 0
VBUS_IN
Wire Wire Line
	3950 1200 4550 1200
Text Label 3950 1200 0    45   ~ 0
SYS
Wire Wire Line
	3950 1300 4550 1300
Text Label 3950 1300 0    45   ~ 0
BAT_P
Wire Wire Line
	3950 1400 4550 1400
Text Label 3950 1400 0    45   ~ 0
BAT_NTC
Wire Wire Line
	3950 1500 4550 1500
Text Label 3950 1500 0    45   ~ 0
GND
$Comp
L VoiceCard:Protected_1S_3000mAh BT1
U 1 1 67AD0002
P 9000 1500
F 0 "BT1" H 9000 1015 50  0000 C CNN
F 1 "Protected_1S_3000mAh" H 9000 1115 50  0000 C CNN
	1    9000 1500
	1    0    0    -1
$EndComp
Wire Wire Line
	7550 1300 8150 1300
Text Label 7550 1300 0    45   ~ 0
BAT_P
Wire Wire Line
	7550 1400 8150 1400
Text Label 7550 1400 0    45   ~ 0
BAT_NTC
Wire Wire Line
	7550 1500 8150 1500
Text Label 7550 1500 0    45   ~ 0
GND
$Comp
L VoiceCard:5k1_CC1 R1
U 1 1 67AD0003
P 1900 2850
F 0 "R1" H 1900 2465 50  0000 C CNN
F 1 "5k1_CC1" H 1900 2565 50  0000 C CNN
	1    1900 2850
	1    0    0    -1
$EndComp
Wire Wire Line
	450 2750 1050 2750
Text Label 450 2750 0    45   ~ 0
CC1
Wire Wire Line
	450 2850 1050 2850
Text Label 450 2850 0    45   ~ 0
GND
$Comp
L VoiceCard:5k1_CC2 R2
U 1 1 67AD0004
P 1900 3550
F 0 "R2" H 1900 3165 50  0000 C CNN
F 1 "5k1_CC2" H 1900 3265 50  0000 C CNN
	1    1900 3550
	1    0    0    -1
$EndComp
Wire Wire Line
	450 3450 1050 3450
Text Label 450 3450 0    45   ~ 0
CC2
Wire Wire Line
	450 3550 1050 3550
Text Label 450 3550 0    45   ~ 0
GND
$Comp
L VoiceCard:Boost_5V U2
U 1 1 67AD0005
P 5400 2830
F 0 "U2" H 5400 2345 50  0000 C CNN
F 1 "Boost_5V" H 5400 2445 50  0000 C CNN
	1    5400 2830
	1    0    0    -1
$EndComp
Wire Wire Line
	3950 2630 4550 2630
Text Label 3950 2630 0    45   ~ 0
SYS
Wire Wire Line
	3950 2730 4550 2730
Text Label 3950 2730 0    45   ~ 0
V5_LOCAL
Wire Wire Line
	3950 2830 4550 2830
Text Label 3950 2830 0    45   ~ 0
GND
$Comp
L VoiceCard:XIAO_USB_plug J2
U 1 1 67AD0006
P 9000 2830
F 0 "J2" H 9000 2245 50  0000 C CNN
F 1 "XIAO_USB_plug" H 9000 2345 50  0000 C CNN
	1    9000 2830
	1    0    0    -1
$EndComp
Wire Wire Line
	7550 2530 8150 2530
Text Label 7550 2530 0    45   ~ 0
V5_LOCAL
Wire Wire Line
	7550 2630 8150 2630
Text Label 7550 2630 0    45   ~ 0
USB_DP
Wire Wire Line
	7550 2730 8150 2730
Text Label 7550 2730 0    45   ~ 0
USB_DM
Wire Wire Line
	7550 2830 8150 2830
Text Label 7550 2830 0    45   ~ 0
GND
$Comp
L VoiceCard:XIAO_Sense_headers U3
U 1 1 67AD0007
P 1850 4750
F 0 "U3" H 1850 3565 50  0000 C CNN
F 1 "XIAO_Sense_headers" H 1850 3665 50  0000 C CNN
	1    1850 4750
	1    0    0    -1
$EndComp
Wire Wire Line
	400 3850 1000 3850
Text Label 400 3850 0    45   ~ 0
REC_N
Wire Wire Line
	400 3950 1000 3950
Text Label 400 3950 0    45   ~ 0
PTT_N
Wire Wire Line
	400 4050 1000 4050
Text Label 400 4050 0    45   ~ 0
SD_CS
Wire Wire Line
	400 4150 1000 4150
Text Label 400 4150 0    45   ~ 0
RTC_SDA
Wire Wire Line
	400 4250 1000 4250
Text Label 400 4250 0    45   ~ 0
RTC_SCL
Wire Wire Line
	400 4350 1000 4350
Text Label 400 4350 0    45   ~ 0
SD_CLK
Wire Wire Line
	400 4450 1000 4450
Text Label 400 4450 0    45   ~ 0
SD_MISO
Wire Wire Line
	400 4550 1000 4550
Text Label 400 4550 0    45   ~ 0
SD_MOSI
Wire Wire Line
	400 4650 1000 4650
Text Label 400 4650 0    45   ~ 0
V3V3
Wire Wire Line
	400 4750 1000 4750
Text Label 400 4750 0    45   ~ 0
GND
$Comp
L VoiceCard:microSD_SPI_3V3 J3
U 1 1 67AD0008
P 5400 4470
F 0 "J3" H 5400 3685 50  0000 C CNN
F 1 "microSD_SPI_3V3" H 5400 3785 50  0000 C CNN
	1    5400 4470
	1    0    0    -1
$EndComp
Wire Wire Line
	3950 3970 4550 3970
Text Label 3950 3970 0    45   ~ 0
V3V3
Wire Wire Line
	3950 4070 4550 4070
Text Label 3950 4070 0    45   ~ 0
SD_CLK
Wire Wire Line
	3950 4170 4550 4170
Text Label 3950 4170 0    45   ~ 0
SD_MOSI
Wire Wire Line
	3950 4270 4550 4270
Text Label 3950 4270 0    45   ~ 0
SD_MISO
Wire Wire Line
	3950 4370 4550 4370
Text Label 3950 4370 0    45   ~ 0
SD_CS
Wire Wire Line
	3950 4470 4550 4470
Text Label 3950 4470 0    45   ~ 0
GND
$Comp
L VoiceCard:PCF8563_module U4
U 1 1 67AD0009
P 9000 4420
F 0 "U4" H 9000 3835 50  0000 C CNN
F 1 "PCF8563_module" H 9000 3935 50  0000 C CNN
	1    9000 4420
	1    0    0    -1
$EndComp
Wire Wire Line
	7550 4120 8150 4120
Text Label 7550 4120 0    45   ~ 0
V3V3
Wire Wire Line
	7550 4220 8150 4220
Text Label 7550 4220 0    45   ~ 0
RTC_SDA
Wire Wire Line
	7550 4320 8150 4320
Text Label 7550 4320 0    45   ~ 0
RTC_SCL
Wire Wire Line
	7550 4420 8150 4420
Text Label 7550 4420 0    45   ~ 0
GND
$Comp
L VoiceCard:Record_NO SW1
U 1 1 67AD000A
P 1870 6100
F 0 "SW1" H 1870 5715 50  0000 C CNN
F 1 "Record_NO" H 1870 5815 50  0000 C CNN
	1    1870 6100
	1    0    0    -1
$EndComp
Wire Wire Line
	420 6000 1020 6000
Text Label 420 6000 0    45   ~ 0
REC_N
Wire Wire Line
	420 6100 1020 6100
Text Label 420 6100 0    45   ~ 0
GND
$Comp
L VoiceCard:Dictate_NO SW2
U 1 1 67AD000B
P 1870 6800
F 0 "SW2" H 1870 6415 50  0000 C CNN
F 1 "Dictate_NO" H 1870 6515 50  0000 C CNN
	1    1870 6800
	1    0    0    -1
$EndComp
Wire Wire Line
	420 6700 1020 6700
Text Label 420 6700 0    45   ~ 0
PTT_N
Wire Wire Line
	420 6800 1020 6800
Text Label 420 6800 0    45   ~ 0
GND
$Comp
L VoiceCard:10k_SD_CS R3
U 1 1 67AD000C
P 5400 5500
F 0 "R3" H 5400 5115 50  0000 C CNN
F 1 "10k_SD_CS" H 5400 5215 50  0000 C CNN
	1    5400 5500
	1    0    0    -1
$EndComp
Wire Wire Line
	3950 5400 4550 5400
Text Label 3950 5400 0    45   ~ 0
V3V3
Wire Wire Line
	3950 5500 4550 5500
Text Label 3950 5500 0    45   ~ 0
SD_CS
$Comp
L VoiceCard:100n_SD C1
U 1 1 67AD000D
P 5400 6140
F 0 "C1" H 5400 5755 50  0000 C CNN
F 1 "100n_SD" H 5400 5855 50  0000 C CNN
	1    5400 6140
	1    0    0    -1
$EndComp
Wire Wire Line
	3950 6040 4550 6040
Text Label 3950 6040 0    45   ~ 0
V3V3
Wire Wire Line
	3950 6140 4550 6140
Text Label 3950 6140 0    45   ~ 0
GND
$Comp
L VoiceCard:47u_SD C2
U 1 1 67AD000E
P 5400 6780
F 0 "C2" H 5400 6395 50  0000 C CNN
F 1 "47u_SD" H 5400 6495 50  0000 C CNN
	1    5400 6780
	1    0    0    -1
$EndComp
Wire Wire Line
	3950 6680 4550 6680
Text Label 3950 6680 0    45   ~ 0
V3V3
Wire Wire Line
	3950 6780 4550 6780
Text Label 3950 6780 0    45   ~ 0
GND
$Comp
L VoiceCard:4k7_SDA R4
U 1 1 67AD000F
P 9000 5500
F 0 "R4" H 9000 5115 50  0000 C CNN
F 1 "4k7_SDA" H 9000 5215 50  0000 C CNN
	1    9000 5500
	1    0    0    -1
$EndComp
Wire Wire Line
	7550 5400 8150 5400
Text Label 7550 5400 0    45   ~ 0
V3V3
Wire Wire Line
	7550 5500 8150 5500
Text Label 7550 5500 0    45   ~ 0
RTC_SDA
$Comp
L VoiceCard:4k7_SCL R5
U 1 1 67AD0010
P 9000 6140
F 0 "R5" H 9000 5755 50  0000 C CNN
F 1 "4k7_SCL" H 9000 5855 50  0000 C CNN
	1    9000 6140
	1    0    0    -1
$EndComp
Wire Wire Line
	7550 6040 8150 6040
Text Label 7550 6040 0    45   ~ 0
V3V3
Wire Wire Line
	7550 6140 8150 6140
Text Label 7550 6140 0    45   ~ 0
RTC_SCL
Text Notes 630 7100 0    55   ~ 0
R1/R2, R4/R5: fit only if absent on the corresponding module. Fit SD decoupling close to the socket.
Text Notes 630 7270 0    55   ~ 0
USB cable or Qi receiver occupies J1. Leave XIAO BAT unused. Use the RTC module backup cell circuit.
$EndSCHEMATC
