# تركيب تايمرات هادي (نقطة 5)

```bash
sudo cp setup/systemd/hadi-*.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now hadi-snapshot-refresh.timer \
  hadi-digest-posthog.timer hadi-digest-marsteam.timer \
  hadi-digest-podaily.timer hadi-digest-followup.timer
systemctl list-timers 'hadi-*'
```

- **مهم:** بعد التفعيل، اوقفوا روتينز كلود القديمة المقابلة (التقرير الصباحي
  والملخصات التلاتة) عشان ميحصلش ازدواج.
- **مهم:** كل الـ 6 units فيها `EnvironmentFile=/home/ubuntu/hadi-ameen-bot/.env`
  — لازم الملف يكون موجود فعلًا في المسار ده على السيرفر، وإلا الـ service
  هيفشل بنفس خطأ `AZURE_DEVOPS_PAT is not set`. لو الـ .env بتاعك في مسار تاني،
  عدّل السطر ده في كل ملف `.service` قبل النسخ.
- تجربة يدوية (لازم تحمّل الـ env الأول لأن السكربتات بتقرا `os.environ` مباشرة،
  مفيهاش dotenv):
  ```bash
  set -a; source .env; set +a
  python3 ado_snapshot.py refresh && python3 ado_snapshot.py brief
  python3 daily_digests.py marsteam --dry-run
  ```
- تقرير الأوتوميشن 10:00 (hadi-mars-results.timer) قايم زي ما هو — مش هنا.
- السجل: `logs/digests.jsonl` + `journalctl -u hadi-digest-*`

## hadi-digest-product-weekly (Product Metrics Report — أسبوعي)

تقرير مؤشرات المنتج الأسبوعي (`intel/weekly_product_metrics.py`). كل الأرقام تُحسب في
بايثون من PostHog مباشرة؛ الـ LLM يكتب التقييم النوعي فقط (لا يحسب أرقامًا). يُسلَّم كـ
DM لآسر عبر `discord_delivery`.

الجدول: كل خميس 12:00 بتوقيت القاهرة.

التفعيل على السيرفر (بعد تشغيل تجريبي ناجح):
```
sudo cp setup/systemd/hadi-digest-product-weekly.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now hadi-digest-product-weekly.timer
```
تشغيل تجريبي يدوي (من غير إرسال):
```
.venv/bin/python intel/weekly_product_metrics.py --dry-run
```
