/**
 * Скрипт для Google Sheets для мгновенного обновления кэша на бэкенде.
 * 
 * ВАЖНО:
 * 1. Зайдите в "Расширения" -> "Apps Script"
 * 2. Вставьте этот код
 * 3. Нажмите на иконку часов слева (Триггеры / Triggers)
 * 4. Нажмите "Добавить триггер" (Add Trigger)
 * 5. Выберите:
 *    - Функция: triggerOnEdit
 *    - Мероприятие: Из таблицы (From spreadsheet)
 *    - Тип события: При редактировании (On edit)
 * 6. Сохраните и выдайте необходимые доступы.
 */

function triggerOnEdit(e) {
  if (!e) return;
  
  var sheet = e.source.getActiveSheet();
  var sheetName = sheet.getName();
  
  // Обновляем кэш только если изменения произошли на листе Catalog
  if (sheetName === "Catalog") {
    invalidateCache();
  }
}

function invalidateCache() {
  // Замените этот URL на адрес вашего сервера на Railway
  var apiUrl = "https://your-backend.up.railway.app/invalidate-cache";
  
  var options = {
    'method' : 'post',
    'muteHttpExceptions': true
  };
  
  try {
    var response = UrlFetchApp.fetch(apiUrl, options);
    Logger.log("Cache invalidate response: " + response.getContentText());
  } catch (err) {
    Logger.log("Ошибка инвалидации кэша: " + err);
  }
}
