// Author: Saulius Lukse

// Copyright: Copyright 2016, kurokesu.com
// version: 0.3
// license: GPL

/* Changelist: 
 * 
 * Rewrite code
 * Always absolute coordinates instead of relative like in v0.1
 * New function: Stop function - M0
 * New function: set current coordinate - G92 Xxx Yyy
 * Reduced power consumption, therefore solved motor heating issue
 * Reversed zoom
 */

/*
+ Add pin definitions
+ Matuoti vartymosi laikus ant seno kodo -> 13.77kHz
+ Kokiu greiciu gali klausyti LV8044? Fclk=8Mhz / 0.128uS
+ vaziavimas i - koordinates -> G92 X4000 Y4000, wait, G92 X0 Y0
*/

#include <avr/io.h>
#include <util/delay.h>

/* a=target variable, b=bit number to act upon 0-n */
#define BIT_SET(a,b) ((a) |= (1<<(b)))
#define BIT_CLEAR(a,b) ((a) &= ~(1<<(b)))
#define BIT_FLIP(a,b) ((a) ^= (1<<(b)))
#define BIT_CHECK(a,b) ((a) & (1<<(b)))

#define MAX_STR    200
#define MAX_ERR    0xFFFF

#define LV8044_DDR_SDATA       DDRB
#define LV8044_DDR_ST          DDRB
#define LV8044_DDR_SCLK        DDRD
#define LV8044_DDR_STB         DDRD

#define LV8044_PIN_SDATA       PINB
#define LV8044_PIN_ST          PINB
#define LV8044_PIN_SCLK        PIND
#define LV8044_PIN_STB         PIND

#define LV8044_PORT_SDATA      PORTB
#define LV8044_PORT_ST         PORTB
#define LV8044_PORT_SCLK       PORTD
#define LV8044_PORT_STB        PORTD

#define LV8044_BIT_SDATA       0 // Nano pin 8
#define LV8044_BIT_ST          2 // Nano pin 10
#define LV8044_BIT_SCLK        4 // Nano pin 4
#define LV8044_BIT_STB         7 // Nano pin 7


#define LV8044_DDR_STEP1       DDRB
#define LV8044_PIN_STEP1       PINB
#define LV8044_PORT_STEP1      PORTB
#define LV8044_BIT_STEP1       1 // Nano pin 9

#define LV8044_DDR_STEP2       DDRD
#define LV8044_PIN_STEP2       PIND
#define LV8044_PORT_STEP2      PORTD
#define LV8044_BIT_STEP2       5 // Nano pin 5


// ****************************************************************************


String inputString = "";         // a string to hold incoming data
boolean stringComplete = false;  // whether the string is complete
unsigned int counter_s1 = 0;
unsigned int counter_s2 = 0;
unsigned int counter_s1_old = 0;
unsigned int counter_s2_old = 0;
unsigned int desired_s1 = 0;
unsigned int desired_s2 = 0;
unsigned int timer_speed = 600;
unsigned int power_value = 1;
uint8_t last_cmd_s1 = 0;
uint8_t last_cmd_s2 = 0;
uint8_t cmd = 0;
unsigned int send_counter = 0;


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



void LV8044_setup()
{
  BIT_SET(LV8044_DDR_SDATA, LV8044_BIT_SDATA);
  BIT_SET(LV8044_DDR_ST, LV8044_BIT_ST);
  BIT_SET(LV8044_DDR_SCLK, LV8044_BIT_SCLK);
  BIT_SET(LV8044_DDR_STB, LV8044_BIT_STB);
  BIT_SET(LV8044_DDR_STEP1, LV8044_BIT_STEP1);
  BIT_SET(LV8044_DDR_STEP2, LV8044_BIT_STEP2);

  BIT_CLEAR(LV8044_PORT_ST, LV8044_BIT_ST);
  BIT_CLEAR(LV8044_PORT_SDATA, LV8044_BIT_SDATA);
  BIT_CLEAR(LV8044_PORT_SCLK, LV8044_BIT_SCLK);
  BIT_CLEAR(LV8044_PORT_STB, LV8044_BIT_STB);
  BIT_CLEAR(LV8044_PORT_STEP1, LV8044_BIT_STEP1);
  BIT_CLEAR(LV8044_PORT_STEP2, LV8044_BIT_STEP2);

  BIT_SET(LV8044_PORT_ST, LV8044_BIT_ST);
  _delay_ms(10); // make sure LV8044 is running before continuing
}


void LV8044_send_byte(int8_t _send)
{
  for(int8_t i=7; i>=0; i--)
  {
    if(BIT_CHECK(_send, i) == 0)
    {
      BIT_CLEAR(LV8044_PORT_SDATA, LV8044_BIT_SDATA);
    }
    else
    {
      BIT_SET(LV8044_PORT_SDATA, LV8044_BIT_SDATA);
    }

    BIT_SET(LV8044_PORT_SCLK, LV8044_BIT_SCLK);  
    //BIT_SET(LV8044_PORT_SCLK, LV8044_BIT_SCLK); // Repeat to extend timing. 0.12us might be to short
    BIT_CLEAR(LV8044_PORT_SCLK, LV8044_BIT_SCLK);  
  }  

    BIT_SET(LV8044_PORT_STB, LV8044_BIT_STB);  
    //BIT_SET(LV8044_PORT_STB, LV8044_BIT_STB); // Repeat to extend timing. 0.12us might be to short  
    BIT_CLEAR(LV8044_PORT_STB, LV8044_BIT_STB);  
}


void set_power(uint8_t p)
{
  // 33%  - 30, 95
  if (p == 1)
  {
    LV8044_send_byte(30);
    LV8044_send_byte(95);
  }
  
  // 50%  - 26, 91
  if (p == 2)
  {
    LV8044_send_byte(26);
    LV8044_send_byte(91);
  }
  
  // 67%  - 28, 93
  if (p == 3)
  {
    LV8044_send_byte(28);
    LV8044_send_byte(93);
  }
                  
  // 100% - 24, 89
  if (p == 4)
  {
    LV8044_send_byte(24);
    LV8044_send_byte(89);
  }
  
  
}

void timer_setup()
{
    cli();          // disable global interrupts
    TCCR1A = 0;     // set entire TCCR1A register to 0
    TCCR1B = 0;     // same for TCCR1B
    OCR1A = timer_speed;   // frequency TODO: set from command interface
    TCCR1B |= (1 << WGM12);
    TCCR1B |= (1 << CS10);
    TIMSK1 |= (1 << OCIE1A);
    sei();
}

ISR(TIMER1_COMPA_vect)
{
    // ------------------------------------------------------------
    if(desired_s1 > counter_s1)
    {
      cmd = 150;
      if(cmd!=last_cmd_s1)
      {
        LV8044_send_byte(cmd);
        last_cmd_s1 = cmd;
      }
      else
      {      
        if (BIT_CHECK(LV8044_PORT_STEP1, LV8044_BIT_STEP1) == 0)
        {   
            BIT_SET(LV8044_PORT_STEP1, LV8044_BIT_STEP1);
        }
        else
        {
            BIT_CLEAR(LV8044_PORT_STEP1, LV8044_BIT_STEP1);
            counter_s1 += 1;
        }
      }
    }

    if(desired_s1 < counter_s1)
    {
      cmd = 134;
      if(cmd!=last_cmd_s1)
      {
        LV8044_send_byte(cmd);
        last_cmd_s1 = cmd;
      }
      else
      {
        if (BIT_CHECK(LV8044_PORT_STEP1, LV8044_BIT_STEP1) == 0)
        {
            BIT_SET(LV8044_PORT_STEP1, LV8044_BIT_STEP1);
        }
        else
        {
            BIT_CLEAR(LV8044_PORT_STEP1, LV8044_BIT_STEP1);
            counter_s1 -= 1;
        }
      }
    }  

    if(desired_s1 == counter_s1)
    {
      cmd = 142; // HOLD

      if(cmd!=last_cmd_s1)
      {
        LV8044_send_byte(cmd);
        last_cmd_s1 = cmd;
      }
    }
    

    // ------------------------------------------------------------
    if(desired_s2 > counter_s2)
    {
      //cmd = 214;
      cmd = 198;
      if(cmd!=last_cmd_s2)
      {
        LV8044_send_byte(cmd);
        last_cmd_s2 = cmd;
      }
      else
      {
        if (BIT_CHECK(LV8044_PORT_STEP2, LV8044_BIT_STEP2) == 0)
        {
            BIT_SET(LV8044_PORT_STEP2, LV8044_BIT_STEP2);
        }
        else
        {
            BIT_CLEAR(LV8044_PORT_STEP2, LV8044_BIT_STEP2);
            counter_s2 += 1;
        }
      }
    }

    if(desired_s2 < counter_s2)
    {
      //cmd = 198;
      cmd = 214;
      if(cmd!=last_cmd_s2)
      {
        LV8044_send_byte(cmd);
        last_cmd_s2 = cmd;
      }
      else
      {
        if (BIT_CHECK(LV8044_PORT_STEP2, LV8044_BIT_STEP2) == 0)
        {
            BIT_SET(LV8044_PORT_STEP2, LV8044_BIT_STEP2);
        }
        else
        {
            BIT_CLEAR(LV8044_PORT_STEP2, LV8044_BIT_STEP2);
            counter_s2 -= 1;
        }
      }
    }  

    if(desired_s2 == counter_s2)
    {
      //cmd = 196; // output off
      cmd = 206; // hold
      if(cmd!=last_cmd_s2)
      {
        LV8044_send_byte(cmd);
        last_cmd_s2 = cmd;
      }
    }


    // if =0 and some time passed, set powersave
    
}




// ****************************************************************************
void setup() 
{
  Serial.begin(115200);
  inputString.reserve(MAX_STR);
  
  while (!Serial) {;} // wait for serial to init
  //Serial.println("Serial is on");
  LV8044_setup();
  timer_setup();
  
  set_power(power_value);
  
  //LV8044_send_byte(150); // 150 - direction=lens.e_direction.CCW, hold=lens.e_hold.CANCEL, counter_reset=lens.e_counter.CANCEL, output=lens.e_output.ON
  //LV8044_send_byte(214); // 214 - direction=lens.e_direction.CCW, hold=lens.e_hold.CANCEL, counter_reset=lens.e_counter.CANCEL, output=lens.e_output.ON 

  LV8044_send_byte(132);
  LV8044_send_byte(196);
}


void loop() 
{
    unsigned int g_starts = 0;
    unsigned int x_starts = 0;
    unsigned int y_starts = 0;
    unsigned int f_starts = 0;
    unsigned int m_starts = 0;
    unsigned int r_starts = 0;
    unsigned int q_starts = 0;
  
    unsigned int g_num = 0;
    unsigned int x_num = 0;
    unsigned int y_num = 0;
    unsigned int f_num = 0;
    unsigned int m_num = 0;
    unsigned int r_num = 0;
    // parsing q is not necessary, we need only one symbol

    if (stringComplete) 
    {
        inputString.toUpperCase();

        g_starts = inputString.indexOf("G"); // G0 - move
        x_starts = inputString.indexOf("X"); 
        y_starts = inputString.indexOf("Y"); 
        f_starts = inputString.indexOf("F"); 
        m_starts = inputString.indexOf("M"); // M commands
        r_starts = inputString.indexOf("R"); // Registers
        q_starts = inputString.indexOf("?"); // report
  
        unsigned int g_num = toInt2(inputString, g_starts+1);
        unsigned int x_num = toInt2(inputString, x_starts+1);
        unsigned int y_num = toInt2(inputString, y_starts+1);
        unsigned int f_num = toInt2(inputString, f_starts+1);
        unsigned int m_num = toInt2(inputString, m_starts+1);
        unsigned int r_num = toInt2(inputString, r_starts+1);

        /*
        if(q_starts == 0)
        {
          Serial.print("!,1=");
          Serial.print(counter_s1);
          
          Serial.print(",2=");
          Serial.print(counter_s2);
          
          Serial.print(",T=");
          Serial.print(timer_speed);

          Serial.print(",P=");
          Serial.print(power_value);

          Serial.print(",C1=");
          Serial.print(last_cmd_s1);

          Serial.print(",C2=");
          Serial.print(last_cmd_s2);

          Serial.println("");
        } 
        */       

        // G0 command
        // Takes X and Y (as S1 and S2 values)
        // For example: G0 X10 Y100
        if (g_num == 0)
        {
          if (x_num != MAX_ERR)
          { 
              desired_s1 = x_num;
          }

          if (y_num != MAX_ERR)
          { 
              desired_s2 = y_num;
          }
        }

        // G92 command
        // sets current position without moving motors
        // used for saving and restoring position
        if (g_num == 92)
        {
          if (x_num != MAX_ERR)
          { 
              desired_s1 = counter_s1 = x_num;
          }

          if (y_num != MAX_ERR)
          { 
              desired_s2 = counter_s2 = y_num;
          }
        }

        // M0 = instant stop
        if (m_num == 0)
        {
            desired_s1 = counter_s1;
            desired_s2 = counter_s2;
        }

        // M99 - speed
        // M99 R100
        // M99 R10000
        // Don't change while moving, there will be glitch and probably missing steps...
        if (m_num == 99)
        {
            if (r_num != MAX_ERR && r_num != 0)
            {
                timer_speed = r_num;
                OCR1A = r_num;
            }
        }

        // M98 - set coil power   
        // M98 R1..4 / 33..100%
        if (m_num == 98)
        {
            if (r_num != MAX_ERR && r_num != 0)
            {
              set_power(r_num);
              power_value = r_num;
            }
        }

        inputString = "";
        stringComplete = false;
        //Serial.println("OK");
        
    } // serial
   

    send_counter += 1;
    if(send_counter > 500)
    {
          Serial.print("!,X=");
          Serial.print(counter_s1);
          
          Serial.print(",Y=");
          Serial.print(counter_s2);
          
          Serial.print(",T=");
          Serial.print(timer_speed);

          Serial.print(",P=");
          Serial.print(power_value);

          Serial.print(",C1=");
          Serial.print(last_cmd_s1);

          Serial.print(",C2=");
          Serial.print(last_cmd_s2);

          Serial.println("");

          send_counter = 0;
    }
}

