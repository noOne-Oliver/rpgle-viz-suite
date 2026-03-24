**free form rpgle**
     D SDS           SDS
     D  PSProgram                  1     10A
     D  PSSystem                   1      6A

     D  Var1            S             10A
     D  Var2            S             10A
     D  Counter         S              5P 0

     D  InputRecord     DS
     D  IRField1                       10A
     D  IRField2                       10A

      /free
        // 初始化
        Var1 = 'Initial';
        Var2 = 'Value';
        Counter = 0;

        // 主循环
        dou Counter > 100;
          Counter += 1;

          if Counter < 50;
            Var1 = 'Processing';
            Var2 = 'Step1';
          else;
            Var1 = 'Complete';
            Var2 = 'Step2';
          endif;

          select;
            when Counter = 10;
              Var1 = 'Milestone1';
            when Counter = 20;
              Var1 = 'Milestone2';
            when Counter = 50;
              Var1 = 'Halfway';
            other;
              Var1 = 'Normal';
          endsl;
        enddo;

        // 输出
        dsply Var1;
        dsply Var2;
        dsply %char(Counter);

        *inlr = *on;
      /end-free
