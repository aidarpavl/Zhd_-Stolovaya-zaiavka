# 🍽️ Столовая школы Жас Дарын

Мектеп асханасына онлайн тапсырыс беру жүйесі.

## 🔗 Деректер көзі
- GitHub: https://github.com/aidarpavl/Stolovaia27
- Мәзір: menu.csv (GitHub-тан оқылады және GitHub-қа сақталады)

## 🚀 Мүмкіндіктер

### 👨‍🎓 Оқушы режимі
- Класс енгізу (1-11 сыныптар)
- Апта таңдау (1-4 апта)
- Күн таңдау (Дүйсенбі–Жұма)
- Санат бойынша сүзу
- Тағамдарды себетке қосу
- Тапсырыс беру

### 👨‍🍳 Асханашы режимі
- Мәзірді өңдеу + **GitHub-қа сақтау**
- Жаңа тағам қосу + **GitHub-қа сақтау**
- Тапсырыстарды қарау
- Есептерді шығару

## 🔐 GitHub токен орнату

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. «Generate new token (classic)» → `repo` рұқсаты
3. Токенді көшіріңіз
4. Streamlit Cloud → App → Settings → Secrets:
   ```toml
   [github]
   token = "ghp_..."
   owner = "aidarpavl"
   repo = "Stolovaia27"
   branch = "main"
   menu_path = "menu.csv"