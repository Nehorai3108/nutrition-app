@echo off
echo פותח פורט 8501 לחיבור מהטלפון...
netsh advfirewall firewall add rule name="Streamlit 8501" dir=in action=allow protocol=TCP localport=8501
echo.
echo הפורט נפתח בהצלחה!
echo עכשיו תוכל לגשת מהטלפון דרך: http://10.0.0.43:8501
echo.
pause
