"""Gives every learning module a pre-test and a post-test.

For each module that has no pre-test and/or no post-test yet, multiple-choice
questions are picked from the question bank below by what the module is about
(its title, topic titles and description). Modules that already have
instructor-written questions keep them: only the missing test is added.

    python manage.py seed_module_quizzes              # add the missing quizzes
    python manage.py seed_module_quizzes --dry-run    # show what would be added
    python manage.py seed_module_quizzes --module fsl-beginner   # one module only

The questions cover concepts and common vocabulary taught in the lessons (not
exact handshapes), so they hold for any module of that subject. Instructors
can edit or replace them in the Quiz Builder.
"""
import re

from django.core.management.base import BaseCommand
from django.db import transaction

from signtext.models import LearningModule, QuizQuestion

PRE_COUNT = 5
POST_COUNT = 10


def q(text, correct, *wrong):
    return {"text": text, "correct": correct, "wrong": list(wrong)}


BANK = {
    "intro": [
        q("What is Filipino Sign Language (FSL)?", "The visual language of the Filipino Deaf community",
          "Spoken Filipino written in hand signs", "A set of random gestures", "English signed word for word"),
        q("Which law declared FSL the national sign language of the Philippines?", "Republic Act 11106",
          "Republic Act 10533", "Republic Act 7277", "Republic Act 9442"),
        q("Does FSL have its own grammar?", "Yes, it has its own grammar and vocabulary",
          "No, it follows English grammar", "No, it follows Filipino grammar", "No, sign languages have no grammar"),
        q("What is a polite way to get a Deaf person's attention?", "Tap them lightly on the shoulder or wave",
          "Shout their name", "Grab their hands", "Stand behind them and wait"),
        q("Why is eye contact important when signing?", "Sign language is visual, so you need to watch the signer",
          "It is not important", "To memorize the signer's face", "Only to show respect to teachers"),
        q("Which of these terms is respectful?", "Deaf / Hard of Hearing", "Deaf and dumb", "Deaf-mute", "Dumb"),
        q("When talking with a Deaf person through an interpreter, you should:", "Look at and talk to the Deaf person directly",
          "Talk only to the interpreter", "Speak louder", "Avoid looking at anyone"),
        q("A name sign is usually:", "Given to you by a member of the Deaf community",
          "Chosen from a dictionary", "Assigned by the school", "The same for everyone"),
        q("Where is most signing done?", "In the signing space in front of the body, from the head to the waist",
          "Behind the back", "Below the knees", "Only beside the ears"),
        q("Which of these is NOT one of the basic parts of a sign?", "Voice volume", "Handshape", "Location", "Movement"),
        q("Changing only the handshape of a sign can:", "Change its meaning",
          "Never change anything", "Make the sign louder", "Turn it into a spoken word"),
        q("Besides the hands, which part of a sign also carries meaning?", "Facial expression",
          "Shoe color", "Clothing", "The signer's height"),
    ],
    "alphabet": [
        q("What is fingerspelling used for?", "Spelling names and words that have no sign",
          "Replacing every sign", "Counting money", "Showing emotions"),
        q("How many letters does the FSL manual alphabet have?", "26", "24", "28", "20"),
        q("Which letters are made with movement (tracing the letter in the air)?", "J and Z", "A and B", "M and N", "O and C"),
        q("Where should your hand be while fingerspelling?", "Near your shoulder, palm facing out",
          "Behind your back", "On your lap", "Covering your mouth"),
        q("Good fingerspelling is:", "Smooth and steady, without bouncing between letters",
          "As fast as possible even if unclear", "Done with your eyes closed", "Done while looking away"),
        q("Which pair of letters looks alike and needs extra care?", "M and N", "A and Z", "J and L", "B and Y"),
        q("If a person's name has no sign yet, you should:", "Fingerspell it",
          "Skip the name", "Make up any sign", "Write it on the floor"),
        q("Which other pair of letters is easy to confuse?", "U and V", "C and X", "D and Z", "F and Q"),
    ],
    "numbers": [
        q("Numbers one to five are shown with:", "The fingers of one hand",
          "Both feet", "Facial expressions only", "Fingerspelling the word"),
        q("To sign your age, you combine:", "The sign for age with a number",
          "Only fingerspelling", "Pointing at a calendar", "Nodding several times"),
        q("Which of these is a number?", "Seven", "Yellow", "Monday", "Father"),
        q("Teen numbers (eleven to nineteen) usually combine:", "Handshapes and movement",
          "One still handshape only", "Spoken words", "Facial expressions only"),
        q("A good way to practice numbers is to sign them:", "In order first, then out of order",
          "Only in order", "Only the even numbers", "Without looking at your hand ever"),
        q("Which of these is NOT a number?", "Green", "Three", "Ten", "Five"),
    ],
    "greetings": [
        q("Which of these is a greeting?", "Good morning", "Rice", "Father", "Yellow"),
        q("Which sign ends a conversation politely?", "Goodbye", "Hello", "Please", "Again"),
        q("Which sign shows appreciation?", "Thank you", "Sorry", "Wait", "No"),
        q('What is a common reply to "Thank you"?', "You're welcome", "Goodbye", "Again", "Maybe"),
        q('Polite signs like "Sorry" and "Please" look sincere when:', "Your facial expression matches them",
          "You sign them very fast", "You look away", "You keep a blank face"),
        q("Which greeting depends on the time of day?", "Good afternoon", "Hello", "Nice to meet you", "Thank you"),
        q('"How are you?" is often answered with:', "I'm fine", "Goodbye", "My name is", "Excuse me"),
        q("To politely interrupt or pass by someone, you sign:", "Excuse me", "Goodbye", "Again", "Yesterday"),
        q("When meeting someone for the first time, you can sign:", "Nice to meet you", "I don't understand", "Wrong", "Wait"),
        q("To introduce yourself, you start with:", "My name is", "See you tomorrow", "How much", "Sorry"),
    ],
    "family": [
        q("Which of these is a family member?", "Grandmother", "Rice", "Monday", "Blue"),
        q("Your father's or mother's sister is your:", "Auntie", "Cousin", "Daughter", "Grandmother"),
        q("Your parents are your:", "Mother and father", "Brother and sister", "Uncle and auntie", "Son and daughter"),
        q("The child of your uncle or auntie is your:", "Cousin", "Son", "Grandfather", "Parent"),
        q("A person who cannot hear and cannot see is described as:", "Deaf-Blind", "Hard of hearing", "Married", "Uncle"),
        q("Which word describes a husband and wife?", "Married", "Cousin", "Boy", "Uncle"),
        q("Your mother's father is your:", "Grandfather", "Uncle", "Son", "Cousin"),
    ],
    "vocabulary": [
        q("Which of these is a color?", "Violet", "Tuesday", "Bread", "Uncle"),
        q("Which of these is a day of the week?", "Wednesday", "December", "Green", "Juice"),
        q("Which of these is a month?", "August", "Friday", "Coffee", "Cousin"),
        q("Signs about the past and the future usually move:", "Backward for the past, forward for the future",
          "Up for the past, down for the future", "Only to the left", "They never move"),
        q("Which of these is a food?", "Rice", "Tea", "Juice", "Coffee"),
        q("Which of these is a drink?", "Juice", "Bread", "Egg", "Fish"),
        q("Which of these is an everyday action?", "Sleep", "Yellow", "Monday", "Auntie"),
        q("Shapes are often signed by:", "Tracing their outline in the air", "Fingerspelling only", "Stomping", "Blinking"),
        q('"Yesterday", "Today" and "Tomorrow" are signs about:', "Time", "Colors", "Food", "Family"),
        q("In FSL, pointing can show:", "Where something or someone is", "That you are angry", "Nothing at all", "Only numbers"),
    ],
    "grammar": [
        q("Where are time signs (like TOMORROW) usually placed in an FSL sentence?", "At the start of the sentence",
          "At the very end", "In the middle of a word", "They are never used"),
        q("How do you make a sentence negative?", "Shake your head while signing", "Nod your head", "Raise your eyebrows", "Sign faster"),
        q("For WH-questions (who, what, where), your eyebrows are usually:", "Lowered", "Raised", "Not moving", "Hidden"),
        q("For yes/no questions, your eyebrows are usually:", "Raised", "Lowered", "Not moving", "Hidden"),
        q("Personal pronouns like I, you, he and she are made by:", "Pointing", "Fingerspelling", "Nodding", "Clapping"),
        q("Possession (my, your) is shown with:", "A flat open hand toward the owner",
          "A closed fist upward", "A head shake", "Pointing at the floor"),
        q("Directional verbs like GIVE and HELP show who does what to whom by:", "The direction of their movement",
          "Their color", "Fingerspelling", "Signing them twice"),
        q("FSL often sets up the topic first, then adds:", "A comment about it", "Fingerspelling", "Nothing else", "A greeting"),
        q("To ask someone to repeat what they signed, sign:", "Can you repeat that", "Goodbye", "Nice to meet you", "Wrong"),
        q("Which of these is a question word?", "Where", "Rice", "Blue", "Mother"),
    ],
    "nonmanual": [
        q("Non-manual signals include:", "Facial expressions, head movements and body posture",
          "Only hand movements", "Spoken words", "Writing on paper"),
        q('When you sign "Happy", your face should:', "Look happy", "Look angry", "Stay blank", "Look away"),
        q("Mouth shapes can add meaning such as:", "Size or intensity", "Nothing", "Sound", "Spelling"),
        q("Nodding while signing usually means:", "Yes (agreement)", "No (negation)", "A WH-question", "Anger"),
        q("Which of these is a feeling?", "Excited", "Bread", "Friday", "Cousin"),
        q("If your face does not match the feeling you sign:", "The message can be confusing",
          "Nothing changes", "It becomes more polite", "It turns into a question"),
    ],
    "classifiers": [
        q("What is a classifier in sign language?",
          "A handshape that stands for a kind of person or object and shows its position or movement",
          "A sign for a number", "A fingerspelled word", "A greeting"),
        q("Classifiers are useful for showing:", "Where things are and how they move", "Only colors", "Only names", "Spoken words"),
        q("The signing space is:", "The area in front of the signer's body, from the head to the waist",
          "Any space behind the signer", "The floor", "The space above the head only"),
        q("After placing a person or object at a spot in the signing space, you can:", "Point to that spot to refer to it again",
          "Never mention it again", "Only fingerspell it every time", "Sign it behind your back"),
        q("Using the signing space like a map helps when:", "Giving directions or describing a room",
          "Counting only", "Saying hello", "Spelling names"),
        q("In storytelling, turning your body and eyes (role shifting) shows:", "Which character is talking or acting",
          "That the story is over", "A number", "A spelling mistake"),
        q("Before using a classifier, signers usually first:", "Sign or spell what the object is",
          "Do nothing", "Stop signing", "Close their eyes"),
    ],
    "practical": [
        q("If you don't understand your teacher's signing, you can sign:", "I don't understand", "Goodbye", "Yellow", "Married"),
        q("In an emergency, one of the most important signs to know is:", "Help", "Yellow", "Bread", "Cousin"),
        q("When giving instructions in sign language, it is best to:", "Give one step at a time and check understanding",
          "Give all steps very fast", "Look away while signing", "Only fingerspell"),
        q("To ask the price at a store, you would use a sign like:", "How much", "Goodbye", "Again", "Sleep"),
        q('"I need help" is used when:', "You need someone to assist you",
          "You are greeting someone", "You are saying goodbye", "You are counting"),
        q("When telling a story in sign language, you usually set up first:", "The time and place",
          "The ending", "The spelling of every word", "Nothing"),
        q("To ask someone to sign more slowly, you can sign:", "Slow", "Fast", "Wrong", "Hot"),
        q("A daily conversation usually starts with:", "A greeting such as Hello", "Goodbye", "Wrong", "A number"),
        q("When giving directions, you can use:", "Your signing space as a map", "Only fingerspelling", "Your feet", "Nothing"),
        q("If someone signs something you understood, you can respond:", "I understand", "Excuse me", "Goodbye", "Again"),
    ],
}

# What a module is about, from its title / topics / description (whole words).
GROUP_RULES = [
    (r"\b(introduc\w*|deaf|culture|etiquette|community|history|basics?|basic sign language|what is fsl)\b", ["intro"]),
    (r"\b(alphabet|finger ?spell\w*|letters?|manual alphabet)\b", ["alphabet"]),
    (r"\b(numbers?|numerical|count\w*|age)\b", ["numbers"]),
    (r"\b(greet\w*|hello|goodbye|polite|courtesy|thank|sorry|please|common expressions?|personal information|introduc\w*)\b", ["greetings"]),
    (r"\b(family|relatives?|relationships?|parents?)\b", ["family"]),
    (r"\b(vocabulary|everyday|colou?rs?|shapes?|days?|months?|time|calendar|food|drinks?|home|objects?|places?|locations?|actions?|activit\w*)\b", ["vocabulary"]),
    (r"\b(sentences?|grammar|questions?|pronouns?|possessives?|verbs?|describ\w*|construction|answer\w*)\b", ["grammar"]),
    (r"\b(facial|non-manual|nonmanual|emotions?|feelings?|expressions)\b", ["nonmanual"]),
    (r"\b(classifiers?|signing space|space|spatial|placement|storytelling)\b", ["classifiers"]),
    (r"\b(classroom|school|help|instructions?|shopping|ordering|directions?|transport\w*|health|emergenc\w*|conversations?|practical|communication)\b", ["practical"]),
]


def groups_for(module) -> list:
    topic_titles = " ".join(module.topics.values_list("title", flat=True))
    found = []
    for text in (f"{module.title} {topic_titles}", module.description or ""):
        for pattern, groups in GROUP_RULES:
            if re.search(pattern, text, re.I):
                for group in groups:
                    if group not in found:
                        found.append(group)
        if found:
            break
    return found or ["intro"]


def question_pool(module) -> list:
    """Questions for the module's subjects, interleaved so each test covers all of them;
    topped up with general FSL questions if the subjects have too few."""
    groups = groups_for(module)
    lists = [list(BANK[g]) for g in groups]
    pool, seen = [], set()
    while any(lists):
        for lst in lists:
            if lst:
                item = lst.pop(0)
                if item["text"] not in seen:
                    seen.add(item["text"])
                    pool.append(item)
    for filler in ("intro", "practical", "greetings"):
        for item in BANK[filler]:
            if len(pool) >= PRE_COUNT + POST_COUNT:
                break
            if item["text"] not in seen:
                seen.add(item["text"])
                pool.append(item)
    return pool


def choices_for(item, index) -> list:
    """The four choices, with the correct one in a different position each time."""
    options = [item["correct"]] + item["wrong"]
    shift = index % len(options)
    return options[shift:] + options[:shift]


class Command(BaseCommand):
    help = "Add a pre-test and a post-test to every learning module that doesn't have them yet."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Show what would be added without saving.")
        parser.add_argument("--module", help="Only this module (module_key).")

    def handle(self, *args, **opts):
        modules = LearningModule.objects.all().order_by("sort_order", "title")
        if opts.get("module"):
            modules = modules.filter(module_key=opts["module"])
        added_tests = 0
        with transaction.atomic():
            for module in modules:
                has_pre = module.quiz_questions.filter(test_type=QuizQuestion.TEST_PRE).exists()
                has_post = module.quiz_questions.filter(test_type=QuizQuestion.TEST_POST).exists()
                if has_pre and has_post:
                    self.stdout.write(f"  keep    {module.title} (already has a pre-test and a post-test)")
                    continue
                pool = question_pool(module)
                # Pre-test and post-test use different questions where possible.
                pre_items = pool[:PRE_COUNT]
                post_items = (pool[PRE_COUNT:] + pool[:PRE_COUNT])[:POST_COUNT]
                plan = []
                if not has_pre:
                    plan.append((QuizQuestion.TEST_PRE, pre_items))
                if not has_post:
                    plan.append((QuizQuestion.TEST_POST, post_items))
                for test_type, items in plan:
                    label = "pre-test" if test_type == QuizQuestion.TEST_PRE else "post-test"
                    self.stdout.write(f"  add     {module.title}: {label} ({len(items)} questions; {', '.join(groups_for(module))})")
                    added_tests += 1
                    if opts["dry_run"]:
                        continue
                    QuizQuestion.objects.bulk_create([
                        QuizQuestion(
                            module=module,
                            test_type=test_type,
                            question_text=item["text"],
                            question_type=QuizQuestion.QUESTION_TYPE_MULTIPLE_CHOICE,
                            choices=choices_for(item, i),
                            correct_answer=item["correct"],
                            order=i + 1,
                        )
                        for i, item in enumerate(items)
                    ])
            if opts["dry_run"]:
                transaction.set_rollback(True)
        self.stdout.write(self.style.SUCCESS(
            f"{'[dry run] ' if opts['dry_run'] else ''}{added_tests} test(s) added."
        ))
