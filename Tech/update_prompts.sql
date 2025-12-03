UPDATE prompts SET text = 'К сожалению, я могу помочь только с вопросами о сервисах Truffles - AI чат-боты для бизнеса. Чем могу помочь в этом направлении?' WHERE name = 'fallback_default';

UPDATE prompts SET text = 'Не совсем понял ваш вопрос. Можете уточнить - вас интересует создание чат-бота, цены или техническая интеграция?' WHERE name = 'clarification_needed';

UPDATE prompts SET text = 'Здравствуйте! Я AI-ассистент компании Truffles. Мы создаём умных чат-ботов для бизнеса с интеграцией WhatsApp, Telegram и Kaspi Pay. Чем могу помочь?' WHERE name = 'greeting_initial';

UPDATE prompts SET text = 'Понял вас. Сейчас передам наш разговор менеджеру - он свяжется с вами в ближайшее время. Спасибо за обращение!' WHERE name = 'handover_to_manager';

SELECT name, LEFT(text, 80) as text_preview FROM prompts ORDER BY id;
