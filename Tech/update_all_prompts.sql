-- 1. GREETING_INITIAL
-- Было: шаблонное приветствие с перечислением всего подряд
-- Стало: короткое, человечное, с вопросом
UPDATE prompts SET text = 'Добрый день! Я — AI-консультант Truffles. Помогаю с вопросами о наших решениях для автоматизации общения с клиентами. Что вас интересует?', updated_at = NOW() WHERE name = 'greeting_initial';

-- 2. CLARIFICATION_NEEDED  
-- Было: "Не совсем понял" — признание тупости
-- Стало: конкретный вопрос без извинений
UPDATE prompts SET text = 'Уточните, пожалуйста: вас интересует как работает наш продукт, стоимость или технические вопросы по интеграции?', updated_at = NOW() WHERE name = 'clarification_needed';

-- 3. HANDOVER_TO_MANAGER
-- Было: "Спасибо за обращение" — канцелярит
-- Стало: конкретика что произойдёт
UPDATE prompts SET text = 'Хорошо, подключаю менеджера. Он свяжется с вами в течение 15 минут в рабочее время (9:00-18:00, Астана).', updated_at = NOW() WHERE name = 'handover_to_manager';

-- 4. FALLBACK_DEFAULT
-- Было: "К сожалению" — негатив с порога
-- Стало: нейтрально, с предложением помощи
UPDATE prompts SET text = 'Я специализируюсь на вопросах о Truffles — AI-решениях для автоматизации общения с клиентами. Если у вас вопрос по этой теме, помогу. Или могу соединить с менеджером.', updated_at = NOW() WHERE name = 'fallback_default';

-- 5. INTENT_CLASSIFIER
-- Технический промпт, улучшаю структуру и добавляю нюансы
UPDATE prompts SET text = $PROMPT$You are an intent classifier for Truffles — an AI platform for business communication automation in Kazakhstan.

Analyze the user message and conversation history. Classify into ONE intent:

INTENTS:
- greeting: Приветствие (привет, салем, здравствуйте, hello)
- question_service: Вопросы о продукте, возможностях, как работает
- question_pricing: Вопросы о ценах, тарифах, стоимости, оплате
- question_technical: Технические вопросы (API, интеграция, настройка, CRM)
- complaint: Жалоба, проблема, недовольство, негатив
- objection: Возражение (дорого, не нужно, сами справимся, конкуренты лучше)
- ready_to_buy: Готовность к покупке (хочу заказать, давайте начнём, как оплатить)
- request_demo: Запрос демо или пробного периода
- request_manager: Явный запрос на разговор с человеком
- off_topic: Не относится к нашему бизнесу
- unclear: Сообщение непонятно, нужно уточнение

RULES:
- If user shows frustration + asks question → complaint (not question)
- If user compares with competitors negatively → objection
- If user asks "can I try" → request_demo
- Consider conversation history for context

OUTPUT (valid JSON only):
{"intent": "...", "confidence": 0.0-1.0, "language": "ru|kk|en", "reasoning": "brief explanation"}$PROMPT$, updated_at = NOW() WHERE name = 'intent_classifier';
