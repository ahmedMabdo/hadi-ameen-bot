#!/usr/bin/env bash
# Watchdog: heartbeat_loop بيلمس logs/alive كل ساعة. لو الملف بقى أقدم من
# MAX_AGE = البوت متعلّق أو ميت من غير crash (الـ Gateway فقد الاتصال مثلًا)
# و systemd مش شايف مشكلة لأن العملية لسه موجودة.
#
# التركيب:
#   sudo cp setup/systemd/hadi-watchdog.{service,timer} /etc/systemd/system/
#   sudo systemctl daemon-reload && sudo systemctl enable --now hadi-watchdog.timer
set -u
BASE=/home/ubuntu/hadi-ameen-bot
ALIVE="$BASE/logs/alive"
MAX_AGE=${HADI_WATCHDOG_MAX_AGE:-7200}   # ساعتين (النبضة كل ساعة)

[ -f "$ALIVE" ] || { echo "watchdog: مفيش $ALIVE لسه - بيتخطى"; exit 0; }
AGE=$(( $(date +%s) - $(stat -c %Y "$ALIVE") ))
if [ "$AGE" -lt "$MAX_AGE" ]; then
  echo "watchdog: ok (عمر النبضة ${AGE}s)"
  exit 0
fi
echo "watchdog: النبضة عمرها ${AGE}s > ${MAX_AGE}s - إعادة تشغيل hadi-discord"
systemctl restart hadi-discord
sleep 20
systemctl is-active --quiet hadi-discord \
  && echo "watchdog: البوت قام تاني" \
  || echo "watchdog: البوت مقامش! محتاج تدخل يدوي"
