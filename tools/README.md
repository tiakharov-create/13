# Инструменты локализации (Android-оболочка Godot)

Скрипты для разбора и правки скомпилированных ресурсов APK без Android SDK.

| файл | назначение |
|---|---|
| `translate.py` | чтение/сборка `ResStringPool` (UTF-8 и UTF-16) |
| `arsc_map.py` | разбор `resources.arsc`: пакеты, пулы типов/ключей, поиск записи по имени ключа |
| `axml.py` | разбор скомпилированного `AndroidManifest.xml` и `res/**/*.xml` (бинарный XML) |
| `dexstrings.py` | разбор `classes.dex` (карта секций, строки, class_data, код методов) |
| `dalvik.py` | таблица размеров инструкций Dalvik (декодер потока кода) |
| `localize_arsc.py` | сам перевод: подмена строк в `resources.arsc` и в layout-файлах |
| `validate.py` | проверка целостности: размеры чанков, границы пулов, конец пакета |

## Проверка

```bash
python3 tools/validate.py resources.arsc
```

## Как правился `resources.arsc`

Строки интерфейса лежат в глобальном пуле строк (`ResStringPool` в начале файла),
а записи типа `string` ссылаются на них по индексу. Поэтому перевод сделан
**заменой значений по месту** (без добавления новых записей): обновляется только
содержимое пула, индексы и все `Res_value` остаются валидными, меняется лишь
`size` чанка пула, `size` пакета и общий размер таблицы.

Переводятся ключи: `dialog_cancel`, `dialog_download`, `dialog_ok`,
`text_error_title`, `error_engine_setup_message`,
`error_missing_vulkan_requirements_message`, `gabe_connection_error_title`,
`gabe_connection_error_message`.

Осознанно **не** переводятся:

* `godot_project_name_string` — «Ascension Sandbox», название игры;
* `status_bar_notification_info_overflow` — «999+», формат числа на бейдже;
* `androidx_startup` — служебное значение, должно совпадать с `meta-data`;
* все имена ресурсов, типов, классов, пакетов и путей.

## Что ещё есть в репозитории

`assets/dexopt/baseline.prof(.m)` — профиль ART, `kotlin/*.kotlin_builtins` —
метаданные Kotlin, `lib/armeabi-v7a/libc++_shared.so`, `libgodot_android.rar`,
`libmonosgen-2.0.rar` — нативные библиотеки, `kotlin-tooling-metadata.json`.

Текстов игры (сцен `.tscn`, переводов `.translation`, `.pck`) в репозитории нет.
