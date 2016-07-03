// Author: Saulius Lukse
// Copyright: Copyright 2016, kurokesu.com
// version: 0.1
// license: GPL

#define ST          10  // PB2
#define STEP1       9   // PB1
#define STEP2       5   // PD5
#define SCLK        4   // PD4
#define SDATA       8   // PB0
#define STB         7   // PD7

#define MOT_DELAY1 200
#define MOT_DELAY2 180
#define MAX_TRAVEL 5000

#define MAX_STR    200
#define MAX_ERR    0xFFFF

void send_byte(unsigned _send)
{
  for(int i=7; i>=0; i--)
  {
    digitalWrite(SDATA, bitRead(_send, i));
    digitalWrite(SCLK, HIGH);
    digitalWrite(SCLK, LOW);
  }  
  digitalWrite(STB, HIGH);
  digitalWrite(STB, LOW);
}

String inputString = "";         // a string to hold incoming data
boolean stringComplete = false;  // whether the string is complete
unsigned int x_counter = 0;
unsigned int y_counter = 0;

void serialEvent() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    inputString += inChar;
    if (inChar == '\n') {
      stringComplete = true;
    }
  }
}

unsigned int toInt2(String text, int offset)
{
  char c = inputString.charAt(offset);
  if ((c>='0' && c<='9') || c=='-')
  {
      unsigned int n = inputString.substring(offset).toInt();
      return n;
  }
  else
  {
      return MAX_ERR;
  }
}

void setup() {
  Serial.begin(115200);
  inputString.reserve(MAX_STR);  
  
  pinMode(ST, OUTPUT);
  pinMode(STEP1, OUTPUT);
  pinMode(STEP2, OUTPUT);
  pinMode(STB, OUTPUT);
  pinMode(SCLK, OUTPUT);
  pinMode(SDATA, OUTPUT);

  digitalWrite(ST, LOW);
  digitalWrite(STEP1, LOW);
  digitalWrite(STEP2, LOW);  
  digitalWrite(SCLK, LOW);
  digitalWrite(SDATA, LOW);
  digitalWrite(STB, LOW);

  digitalWrite(ST, HIGH);
  delay(10);
}


void loop() {
  unsigned int g_starts = 0;
  unsigned int x_starts = 0;
  unsigned int y_starts = 0;
  unsigned int f_starts = 0;
  unsigned int m_starts = 0;
  unsigned int r_starts = 0;

  unsigned int g_num = 0;
  unsigned int x_num = 0;
  unsigned int y_num = 0;
  unsigned int f_num = 0;
  unsigned int m_num = 0;
  unsigned int r_num = 0;

  if (stringComplete) {
      inputString.toUpperCase();

      g_starts = inputString.indexOf("G");
      x_starts = inputString.indexOf("X");
      y_starts = inputString.indexOf("Y");
      f_starts = inputString.indexOf("F");
      m_starts = inputString.indexOf("M");
      r_starts = inputString.indexOf("R");

      unsigned int g_num = toInt2(inputString, g_starts+1);
      unsigned int x_num = toInt2(inputString, x_starts+1);
      unsigned int y_num = toInt2(inputString, y_starts+1);
      unsigned int f_num = toInt2(inputString, f_starts+1);
      unsigned int m_num = toInt2(inputString, m_starts+1);
      unsigned int r_num = toInt2(inputString, r_starts+1);

      if (m_num == 99)
      {
        if (r_num >=0 && r_num <0x100)
        {
          send_byte(r_num);
          Serial.println("OK");
        }
      }

      if (g_num == 0)
      {
        if (x_num != MAX_ERR && f_num != MAX_ERR)
        { 
            for(int i = 0; i<x_num; i++)
            {
              digitalWrite(STEP1, HIGH);
              delayMicroseconds(f_num);    
          
              digitalWrite(STEP1, LOW);
              delayMicroseconds(f_num);   
            }
            Serial.println("OK");
        }

        if (y_num != MAX_ERR && f_num != MAX_ERR)
        { 
            for(int i = 0; i<y_num; i++)
            {
              digitalWrite(STEP2, HIGH);
              delayMicroseconds(f_num);    
          
              digitalWrite(STEP2, LOW);
              delayMicroseconds(f_num);   
            }
            Serial.println("OK");
        }        
      }

    inputString = "";
    stringComplete = false;
  }
}


