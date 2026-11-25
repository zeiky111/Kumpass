"""Seeds the recommended KUMPAS FSL curriculum (Beginner -> Intermediate ->
Advanced): Beginner has two modules (Basic Sign Language, then Everyday
Vocabulary), Intermediate and Advanced one each -- each with its lesson topics
and the sign words each topic teaches. (--split instead creates one module per
topic area.)

Safe to run more than once. Modules are matched by module_key; an existing
module is left alone unless --update is given. Modules are created as drafts
so instructors can add materials, pre-/post-tests and videos before
publishing (a published module with no post-test can never be "finished",
which would keep the next level locked for every student).

    python manage.py seed_fsl_curriculum               # create missing modules as drafts
    python manage.py seed_fsl_curriculum --publish     # create them already published
    python manage.py seed_fsl_curriculum --update      # also rewrite title/description/topics of existing ones
    python manage.py seed_fsl_curriculum --dry-run     # show what would happen
    python manage.py seed_fsl_curriculum --split       # 28 modules (one per topic area) instead of 4
    python manage.py seed_fsl_curriculum --update      # rewrite modules that already exist (e.g. an old
                                                       # "Elementary" module becomes "Beginner – Everyday Vocabulary")
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models.functions import Lower

from signtext.models import LearningModule, ModuleTopic, SignVideo

B = LearningModule.LEVEL_BEGINNER
I = LearningModule.LEVEL_INTERMEDIATE
A = LearningModule.LEVEL_ADVANCED
# Not a level (there is no Elementary level): the "Everyday Vocabulary" group,
# taught as the second Beginner module.
E = "everyday-vocabulary"
GROUP_LEVEL = {B: B, E: B, I: I, A: A}

ALPHABET = [chr(c) for c in range(ord("A"), ord("Z") + 1)]


def topic(title, content, signs=()):
    return {"title": title, "content": content, "sign_words": list(signs)}


# (module_key, level, title, description, [topics])
CURRICULUM = [
    # ------------------------------------------------------------------
    # BEGINNER - Basic Sign Language
    # Focus: Familiarization with FSL and basic hand signs.
    # ------------------------------------------------------------------
    ("fsl-b1-intro", B, "Introduction to Filipino Sign Language",
     "Get to know FSL: what it is, who uses it, and the basics of signing.",
     [
         topic("What is FSL?",
               "Filipino Sign Language (FSL) is the visual language of the Filipino Deaf community. "
               "It has its own grammar and vocabulary and is not signed English or signed Filipino. "
               "Republic Act 11106 declared FSL the national sign language of the Philippines."),
         topic("The Deaf Community",
               "Learn respectful terms for people in the community. Many Deaf people see themselves as part "
               "of a cultural and language group, not as people with a deficiency.",
               ["Deaf", "Hard Of Hearing", "Deaf-Blind"]),
         topic("Parts of a Sign",
               "Every sign is made of handshape, location, movement and palm orientation, plus facial "
               "expression. Changing any one of these can change the meaning of a sign."),
         topic("Signing Etiquette",
               "Keep eye contact, sign within the signing space (head to waist), and get a Deaf person's "
               "attention with a light tap on the shoulder or a wave, never by grabbing their hands."),
     ]),
    ("fsl-b2-alphabet", B, "FSL Alphabet (A–Z)",
     "Fingerspell every letter of the FSL manual alphabet.",
     [
         topic("Letters A–I",
               "Practice each handshape slowly. Keep your signing hand at shoulder height with the palm facing out.",
               ALPHABET[0:9]),
         topic("Letters J–R",
               "J and Z use movement: trace the letter shape in the air.",
               ALPHABET[9:18]),
         topic("Letters S–Z",
               "Watch closely for letters that look alike, such as M/N and U/V.",
               ALPHABET[18:26]),
         topic("Fingerspelling Words",
               "Fingerspell names and words that have no sign. Spell smoothly without bouncing your hand "
               "between letters. Try spelling your own name."),
     ]),
    ("fsl-b3-numbers", B, "Numbers (0–20)",
     "Count and sign numbers from zero to twenty.",
     [
         topic("Numbers 0–5", "Numbers one to five are shown with the fingers of one hand.",
               ["Zero", "One", "Two", "Three", "Four", "Five"]),
         topic("Numbers 6–10", "Practice switching quickly between numbers.",
               ["Six", "Seven", "Eight", "Nine", "Ten"]),
         topic("Numbers 11–20", "Teen numbers combine handshapes and movement. Practice them in order, then out of order.",
               ["Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen",
                "Sixteen", "Seventeen", "Eighteen", "Nineteen", "Twenty"]),
     ]),
    ("fsl-b4-greetings", B, "Basic Greetings",
     "Say hello, greet people at different times of day, and say goodbye.",
     [
         topic("Hello and Welcome", "Start every conversation with a greeting and a friendly face.",
               ["Hello", "Welcome", "Nice To Meet You"]),
         topic("Time-of-Day Greetings", "Greet people according to the time of day.",
               ["Good Morning", "Good Afternoon", "Good Evening"]),
         topic("How Are You?", "Ask how someone is and answer the question.",
               ["How Are You", "I'm Fine"]),
         topic("Saying Goodbye", "End a conversation politely.",
               ["Goodbye", "See You Tomorrow"]),
     ]),
    ("fsl-b5-expressions", B, "Common Expressions",
     "Use polite everyday expressions like thank you, sorry and please.",
     [
         topic("Thank You and You're Welcome", "Show appreciation and respond to thanks.",
               ["Thank you", "You're welcome"]),
         topic("Please, Sorry and Excuse Me", "Polite expressions need a matching facial expression to sound sincere.",
               ["Please", "Sorry", "Excuse me"]),
         topic("Yes, No and Maybe", "Answer simple questions.",
               ["Yes", "No", "Maybe"]),
         topic("Checking Understanding", "Let the other person know whether you understood.",
               ["I understand", "I don't understand", "Again", "Can you repeat that"]),
     ]),
    ("fsl-b6-personal-info", B, "Basic Personal Information",
     "Introduce yourself: your name, age and where you live.",
     [
         topic("My Name Is…", "Introduce yourself and fingerspell your name.",
               ["My name is", "What is your name", "Nice to meet you"]),
         topic("Name Signs", "In the Deaf community, a name sign is given to you by a Deaf person. "
               "Until then, fingerspell your name."),
         topic("My Age", "Combine the sign for age with the numbers you learned.",
               ["Age", "How Old"]),
         topic("Where I Live", "Tell others where you live.",
               ["Address", "Live", "Where"]),
     ]),

    # ------------------------------------------------------------------
    # BEGINNER (2nd module) - Everyday Vocabulary
    # Focus: Learning commonly used words and expressions.
    # ------------------------------------------------------------------
    ("fsl-e1-family", E, "Family Members",
     "Sign the people in your family.",
     [
         topic("Parents", "Learn signs for your parents.", ["Mother", "Father", "Parents"]),
         topic("Children", "Signs for sons and daughters.", ["Son", "Daughter", "Boy", "Girl"]),
         topic("Grandparents", "Signs for grandparents.", ["Grandmother", "Grandfather"]),
         topic("Extended Family", "Relatives outside your immediate family.",
               ["Auntie", "Uncle", "Cousin", "Brother", "Sister"]),
     ]),
    ("fsl-e2-colors-shapes", E, "Colors and Shapes",
     "Describe things by their color and shape.",
     [
         topic("Basic Colors", "Primary and common colors.", ["Red", "Blue", "Yellow", "Green", "Orange", "Violet"]),
         topic("More Colors", "Neutral colors and shades.", ["Black", "White", "Gray", "Brown", "Pink", "Light", "Dark"]),
         topic("Shapes", "Shapes are often signed by tracing their outline in the air.",
               ["Circle", "Square", "Triangle", "Rectangle"]),
     ]),
    ("fsl-e3-time", E, "Days, Months, and Time",
     "Talk about days of the week, months of the year, and time.",
     [
         topic("Days of the Week", "Sign each day of the week.",
               ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]),
         topic("Yesterday, Today, Tomorrow", "Signs for past and future move backward and forward from your body.",
               ["Yesterday", "Today", "Tomorrow"]),
         topic("Months (January–June)", "The first half of the year.",
               ["January", "February", "March", "April", "May", "June"]),
         topic("Months (July–December)", "The second half of the year.",
               ["July", "August", "September", "October", "November", "December"]),
         topic("Telling Time", "Ask and tell the time using numbers.", ["Time", "Hour", "Minute"]),
     ]),
    ("fsl-e4-food-drinks", E, "Food and Drinks",
     "Name common Filipino food and drinks.",
     [
         topic("Eating and Drinking", "The basic actions.", ["Eat", "Drink", "Food", "Water"]),
         topic("Common Food", "Everyday Filipino meals.",
               ["Rice", "Bread", "Egg", "Chicken", "Fish", "Meat", "Longanisa", "Spaghetti", "Shrimp", "Crab"]),
         topic("Drinks", "Common drinks.", ["Coffee", "Tea", "Milk", "Juice"]),
         topic("Describing Food and Drinks", "Say how you like it.", ["Hot", "Cold", "Sugar", "No Sugar"]),
     ]),
    ("fsl-e5-home-objects", E, "Common Objects at Home",
     "Sign things you find around the house.",
     [
         topic("Rooms", "Parts of the house.", ["House", "Bedroom", "Kitchen", "Bathroom"]),
         topic("Furniture", "Things you sit, sleep or eat on.", ["Table", "Chair", "Bed", "Door", "Window"]),
         topic("Everyday Items", "Things you use every day.", ["Phone", "Television", "Cup", "Plate"]),
     ]),
    ("fsl-e6-places", E, "Places and Locations",
     "Name places in your community.",
     [
         topic("Around the Community", "Places you visit often.", ["School", "Church", "Market", "Store"]),
         topic("Public Places", "Places that offer services.", ["Hospital", "Park", "Office", "Bank"]),
         topic("Here and There", "Pointing is part of FSL grammar: point to show where something is.",
               ["Here", "There", "Near", "Far"]),
     ]),
    ("fsl-e7-actions", E, "Common Actions and Activities",
     "Sign everyday activities.",
     [
         topic("Daily Routine", "Things you do every day.", ["Sleep", "Eat", "Drink", "Work"]),
         topic("School Activities", "Things you do in class.", ["Study", "Read", "Write"]),
         topic("Movement", "Moving from place to place.", ["Go", "Come", "Walk", "Play"]),
     ]),

    # ------------------------------------------------------------------
    # INTERMEDIATE - Sentence Construction
    # Focus: Combining signs to express complete thoughts.
    # ------------------------------------------------------------------
    ("fsl-i1-sentences", I, "Basic Sentence Formation",
     "Combine signs into simple, complete sentences.",
     [
         topic("FSL Word Order", "FSL often sets up the topic first, then comments on it "
               "(e.g. RICE, I EAT). Word order is flexible, but the topic usually comes first."),
         topic("Time First", "Put time signs at the start of a sentence: TOMORROW I GO SCHOOL.",
               ["Today", "Tomorrow", "Yesterday"]),
         topic("Negation", "Shake your head while signing to make a sentence negative.",
               ["No", "Don't Know", "Don't Understand"]),
     ]),
    ("fsl-i2-question-words", I, "Question Words",
     "Ask questions with who, what, where, when, why and how.",
     [
         topic("Who, What, Where", "Lower your eyebrows when asking WH-questions.",
               ["Who", "What", "Where"]),
         topic("When, Why, How", "The question word usually comes at the end of the sentence.",
               ["When", "Why", "How"]),
         topic("Yes/No Questions", "Raise your eyebrows and lean slightly forward for yes/no questions.",
               ["Yes", "No"]),
     ]),
    ("fsl-i3-pronouns", I, "Pronouns and Possessives",
     "Point to people and show ownership.",
     [
         topic("Personal Pronouns", "Pronouns are made by pointing: to yourself (I), the person you "
               "are talking to (you), or someone else (he/she).",
               ["I", "You", "He", "She", "We", "They"]),
         topic("Possessives", "Use a flat open hand toward the owner to show possession.",
               ["My", "Your", "His", "Her", "Our", "Their"]),
     ]),
    ("fsl-i4-verbs", I, "Common Verbs and Actions",
     "Use verbs in sentences.",
     [
         topic("Everyday Verbs", "Common actions.", ["Eat", "Drink", "Sleep", "Work", "Study", "Read", "Write"]),
         topic("Thinking Verbs", "Verbs about the mind.", ["Know", "Understand", "Want", "Like", "Need"]),
         topic("Directional Verbs", "Some verbs move from the subject to the object, such as GIVE and HELP. "
               "The direction tells you who does what to whom.",
               ["Give", "Help", "Ask", "Tell"]),
     ]),
    ("fsl-i5-describing", I, "Describing People and Objects",
     "Use adjectives to describe people and things.",
     [
         topic("Describing People", "Describe how someone looks.",
               ["Tall", "Short", "Man", "Woman", "Boy", "Girl"]),
         topic("Describing Objects", "Describe size, color and quality.",
               ["Big", "Small", "Hot", "Cold", "Fast", "Slow"]),
         topic("Right and Wrong", "Give feedback on answers.", ["Correct", "Wrong"]),
     ]),
    ("fsl-i6-qa", I, "Asking and Answering Questions",
     "Hold a short question-and-answer exchange.",
     [
         topic("Getting to Know Someone", "Ask and answer introduction questions.",
               ["What is your name", "My name is", "How are you", "I'm fine"]),
         topic("Clarifying", "Ask the other person to repeat or slow down.",
               ["Can you repeat that", "Again", "Slow", "Wait"]),
         topic("Short Answers", "Answer briefly and clearly.",
               ["Yes", "No", "Maybe", "Know", "Don't Know"]),
     ]),
    ("fsl-i7-feelings", I, "Expressing Feelings and Emotions",
     "Express how you feel, with matching facial expressions.",
     [
         topic("Basic Feelings", "Your face must match the feeling you sign.",
               ["Happy", "Sad", "Angry", "Afraid"]),
         topic("More Feelings", "Feelings in everyday life.", ["Tired", "Excited", "Love"]),
         topic("Asking About Feelings", "Ask how someone feels and respond with care.",
               ["How are you", "Sorry"]),
     ]),

    # ------------------------------------------------------------------
    # ADVANCED - Practical Communication
    # Focus: Applying FSL in different situations.
    # ------------------------------------------------------------------
    ("fsl-a1-classroom", A, "Classroom Communication",
     "Communicate with teachers and classmates in class.",
     [
         topic("Classroom Signs", "Signs used every day in class.",
               ["Teacher", "Student", "Study", "Read", "Write"]),
         topic("Following the Lesson", "Tell your teacher when you understand or need help.",
               ["I understand", "I don't understand", "Can you repeat that", "Slow"]),
     ]),
    ("fsl-a2-school", A, "School-Related Conversations",
     "Talk about school life, subjects and schedules.",
     [
         topic("Schedules", "Talk about when classes happen.",
               ["Monday", "Friday", "Today", "Tomorrow", "Time"]),
         topic("Subjects and Tasks", "Talk about subjects and homework.",
               ["Math", "Science", "English", "Homework", "Test"]),
     ]),
    ("fsl-a3-help-instructions", A, "Asking for Help and Giving Instructions",
     "Ask for help politely and give clear step-by-step instructions.",
     [
         topic("Asking for Help", "Combine polite expressions with the sign for help.",
               ["I need help", "Help", "Please", "Excuse me"]),
         topic("Giving Instructions", "Give one instruction at a time and check for understanding.",
               ["Wait", "Again", "Slow", "Fast", "Correct", "Wrong"]),
     ]),
    ("fsl-a4-shopping-food", A, "Shopping and Ordering Food",
     "Buy things and order food and drinks.",
     [
         topic("At the Store", "Ask for items and prices.", ["Buy", "How Much", "Money", "Store"]),
         topic("Ordering Food", "Order a meal and drink.",
               ["Rice", "Chicken", "Coffee", "Juice", "Water", "No Sugar", "Thank you"]),
     ]),
    ("fsl-a5-directions", A, "Directions and Transportation",
     "Give and follow directions and talk about getting around.",
     [
         topic("Giving Directions", "Use your signing space as a map.",
               ["Left", "Right", "Straight", "Near", "Far", "Where"]),
         topic("Transportation", "Common ways to travel in the Philippines.",
               ["Jeepney", "Tricycle", "Bus", "Car", "Walk"]),
     ]),
    ("fsl-a6-health-emergency", A, "Health and Emergency Situations",
     "Communicate when someone is sick, hurt or in danger.",
     [
         topic("Feeling Sick", "Describe symptoms and where it hurts.",
               ["Sick", "Pain", "Headache", "Fever", "Tired"]),
         topic("Getting Help", "Signs to use in an emergency.",
               ["Help", "I need help", "Doctor", "Hospital", "Emergency", "Police", "Fire"]),
     ]),
    ("fsl-a7-conversations", A, "Daily Conversations and Storytelling",
     "Hold longer conversations and tell simple stories.",
     [
         topic("Daily Conversations", "Bring together greetings, questions and responses.",
               ["Hello", "How are you", "I'm fine", "What", "Why"]),
         topic("Storytelling Basics", "Set the time and place first, then use space and role shifting "
               "to show different characters.",
               ["Yesterday", "Today", "Tomorrow"]),
     ]),
    ("fsl-a8-nms", A, "FSL Facial Expressions and Non-Manual Signals",
     "Use your face, head and body as part of the grammar of FSL.",
     [
         topic("Eyebrows and Questions", "Raised eyebrows for yes/no questions; lowered eyebrows for WH-questions."),
         topic("Head Movements", "Nod to affirm and shake your head to negate a sentence.", ["Yes", "No"]),
         topic("Mouth Morphemes", "Mouth shapes add meaning, such as size, intensity or ease."),
         topic("Emotion on the Face", "Your facial expression carries the emotion of what you sign.",
               ["Happy", "Sad", "Angry", "Excited"]),
     ]),
]


# Default layout: ONE module per level, and each entry of CURRICULUM above
# becomes one TOPIC of that module (its sub-topics are folded into the topic's
# lesson text, and their sign words are combined). --split keeps the older
# layout of one module per CURRICULUM entry.
LEVEL_MODULES = {
    B: ("fsl-beginner", "Beginner – Basic Sign Language",
        "Focus: Familiarization with FSL and basic hand signs."),
    # Key kept as "fsl-elementary" so a module seeded before the Elementary
    # level was removed is matched (and fixed with --update), not duplicated.
    E: ("fsl-elementary", "Beginner – Everyday Vocabulary",
        "Focus: Learning commonly used words and expressions."),
    I: ("fsl-intermediate", "Intermediate – Sentence Construction",
        "Focus: Combining signs to express complete thoughts."),
    A: ("fsl-advanced", "Advanced – Practical Communication",
        "Focus: Applying FSL in different situations."),
}


def level_curriculum():
    """CURRICULUM regrouped as [(module_key, level, title, description, topics)], one module per group."""
    grouped = []
    for group in (B, E, I, A):
        key, title, description = LEVEL_MODULES[group]
        topics = []
        for _key, entry_group, entry_title, entry_description, sub_topics in CURRICULUM:
            if entry_group != group:
                continue
            # Topic text: the entry's summary, then each sub-topic as its own
            # paragraph ("Sub-topic: text"); the topic viewer shows blank-line
            # separated blocks as paragraphs.
            paragraphs = [entry_description] + [f"{t['title']}: {t['content']}" for t in sub_topics]
            words, seen = [], set()
            for t in sub_topics:
                for word in t["sign_words"]:
                    if word.lower() not in seen:
                        seen.add(word.lower())
                        words.append(word)
            topics.append(topic(entry_title, "\n\n".join(paragraphs), words))
        grouped.append((key, GROUP_LEVEL[group], title, description, topics))
    return grouped


class Command(BaseCommand):
    help = "Seed the KUMPAS FSL curriculum (Beginner, Intermediate, Advanced modules and topics)."

    def add_arguments(self, parser):
        parser.add_argument("--split", action="store_true",
                            help="One module per topic area (28 modules) instead of one module per level (4 modules).")
        parser.add_argument("--publish", action="store_true", help="Create new modules as published instead of draft.")
        parser.add_argument("--update", action="store_true",
                            help="Also rewrite title, description, level and topics of modules that already exist "
                                 "(topic completions for replaced topics are lost).")
        parser.add_argument("--dry-run", action="store_true", help="Show what would change without saving.")

    def handle(self, *args, **opts):
        publish, update, dry = opts["publish"], opts["update"], opts["dry_run"]
        created = updated = skipped = 0

        plan = (
            [(key, GROUP_LEVEL[group], title, description, topics) for key, group, title, description, topics in CURRICULUM]
            if opts["split"] else level_curriculum()
        )
        with transaction.atomic():
            for index, (key, level, title, description, topics) in enumerate(plan):
                sort_order = index + 1
                module = LearningModule.objects.filter(module_key=key).first()
                if module and not update:
                    skipped += 1
                    self.stdout.write(f"  skip    {key} (exists)")
                    continue

                if module is None:
                    module = LearningModule(
                        module_key=key,
                        status=LearningModule.STATUS_PUBLISHED if publish else LearningModule.STATUS_DRAFT,
                    )
                    action = "create"
                    created += 1
                else:
                    action = "update"
                    updated += 1

                module.title = title
                module.year_level = level
                module.description = description
                module.sort_order = sort_order
                module.activities_count = len(topics)
                self.stdout.write(f"  {action:<7} [{level}] {title} ({len(topics)} topics)")
                if dry:
                    continue
                module.save()
                module.topics.all().delete()
                ModuleTopic.objects.bulk_create([
                    ModuleTopic(module=module, title=t["title"], content=t["content"],
                                sign_words=t["sign_words"], order=i + 1)
                    for i, t in enumerate(topics)
                ])

            if dry:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f"{'[dry run] ' if dry else ''}{created} created, {updated} updated, {skipped} skipped."
        ))
        self._report_missing_videos()

    def _report_missing_videos(self):
        words = {w for *_, topics in CURRICULUM for t in topics for w in t["sign_words"]}
        have = set(
            SignVideo.objects.filter(is_published=True)
            .annotate(w=Lower("word")).values_list("w", flat=True)
        )
        missing = sorted(w for w in words if w.lower() not in have)
        if missing:
            self.stdout.write(self.style.WARNING(
                f"{len(missing)} sign word(s) have no published video yet (shown as 'missing' to students):"
            ))
            self.stdout.write("  " + ", ".join(missing))
