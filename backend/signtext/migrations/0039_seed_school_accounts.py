from django.conf import settings
from django.db import migrations

# Instructor and student logins for the school, 10 instructors and 30
# students across year levels 1-4. Only password hashes are stored.
# If an account already exists, its name is kept and only the password,
# role and year level are set.
ACCOUNTS = [
    {"email": "marvin.delarosa@gmail.com", "role": "instructor", "first_name": "Marvin", "last_name": "Dela Rosa", "year_level": "", "password_hash": "pbkdf2_sha256$870000$ktpeibsrG3Z1SodE1rVZ9R$ja2BIWIZKfqCtYxvhD4Qt/DC5Gwkcp/+C2yns8CLfmw="},
    {"email": "teresita.lacson@gmail.com", "role": "instructor", "first_name": "Teresita", "last_name": "Lacson", "year_level": "", "password_hash": "pbkdf2_sha256$870000$DQqBPWoiyi1fBvQYcyPO9S$ND0i7CkZWrcwMc9nTMXKHZRELrbZ5W2dTUu1Kd1eRA8="},
    {"email": "rolando.magbanua@gmail.com", "role": "instructor", "first_name": "Rolando", "last_name": "Magbanua", "year_level": "", "password_hash": "pbkdf2_sha256$870000$6xR5R9GZQFUlR9JS3o5X75$jrr3n+ziL7oZ9ShzQyGObs3jtYin9x3gEyVEX4xHwKM="},
    {"email": "evangeline.robles@gmail.com", "role": "instructor", "first_name": "Evangeline", "last_name": "Robles", "year_level": "", "password_hash": "pbkdf2_sha256$870000$Svp0nMq4X8gW8cZ8IM96Dz$HrB99TWgRDgsgy5tGVijbB1nvsCKQ4TOiCo8goOzUTQ="},
    {"email": "danilo.cabrera@gmail.com", "role": "instructor", "first_name": "Danilo", "last_name": "Cabrera", "year_level": "", "password_hash": "pbkdf2_sha256$870000$wqh3KQax1C7924HTXDo99h$iDod1tARxwNSXFO7hMlwjLnM+XzD5pE2dd392TCca6g="},
    {"email": "maricar.javier@gmail.com", "role": "instructor", "first_name": "Maricar", "last_name": "Javier", "year_level": "", "password_hash": "pbkdf2_sha256$870000$sA7TkLLqwv6IHNKZ5pT1He$FHPHrMJe3H+DUvbpX79Syr7yQye9mEAEtLh/tjWTsis="},
    {"email": "reynaldo.sison@gmail.com", "role": "instructor", "first_name": "Reynaldo", "last_name": "Sison", "year_level": "", "password_hash": "pbkdf2_sha256$870000$LmGq0kXr7ISrO4ZjsVD5Po$FzlXxnPJbntBQudGYU38w/raODV1GvdYs7x/BQ67t/s="},
    {"email": "gina.padilla@gmail.com", "role": "instructor", "first_name": "Gina", "last_name": "Padilla", "year_level": "", "password_hash": "pbkdf2_sha256$870000$JVTuWxvhiU1h4cYE9PETO9$ZZnwRlc6XeaRDACCCIOVS7ZhWqDiwirt+jwfxLTCBe0="},
    {"email": "alvin.rosales@gmail.com", "role": "instructor", "first_name": "Alvin", "last_name": "Rosales", "year_level": "", "password_hash": "pbkdf2_sha256$870000$6qMHussCU9VwYx7QuN6yQg$yGzRt7cV4cx0Vjk9FYHxSkPYQr1L25cWg1JiAp0N9/E="},
    {"email": "sheila.bernardo@gmail.com", "role": "instructor", "first_name": "Sheila", "last_name": "Bernardo", "year_level": "", "password_hash": "pbkdf2_sha256$870000$VsKfc5OmduSPQRJ4xF3ENE$u7PQN5Qaq+Rb1QkolAR+Mzc4tKhJLm3gews4+fw7weY="},
    {"email": "jhonlloyd.abad@gmail.com", "role": "student", "first_name": "Jhon Lloyd", "last_name": "Abad", "year_level": "1", "password_hash": "pbkdf2_sha256$870000$QIb8uvN3jBjPD8IOaUwFol$pGtX10yOvo5nyClNhEfYUxCeM9umSU9GQyATmq66x9U="},
    {"email": "maangela.rivera08@gmail.com", "role": "student", "first_name": "Ma. Angela", "last_name": "Rivera", "year_level": "1", "password_hash": "pbkdf2_sha256$870000$BclDoycXB8D1wOatn4IOHR$iRQTxdHYyZ8C997XNqCwoOPvxdqLvR15ksK6lR3aVTM="},
    {"email": "kurt.esguerra.2006@gmail.com", "role": "student", "first_name": "Kurt", "last_name": "Esguerra", "year_level": "1", "password_hash": "pbkdf2_sha256$870000$HHq8a85kQ0YpFI8IiGZwZT$zM+Rua2s6DMqPXEnarlp9mCzlHfA1tCP4bO8SKXpTS0="},
    {"email": "ellamae.fajardo1@gmail.com", "role": "student", "first_name": "Ella Mae", "last_name": "Fajardo", "year_level": "1", "password_hash": "pbkdf2_sha256$870000$EmIhXnGjhxIrsal1xqq72m$auwDCGAxnjQ63DGD07f9DgSISG3JpWGFdXWLIl7AaJw="},
    {"email": "justine.concepcion@gmail.com", "role": "student", "first_name": "Justine", "last_name": "Concepcion", "year_level": "1", "password_hash": "pbkdf2_sha256$870000$cbx6B46wMIV9naYagihLCY$KW5DFK0Kh4iy5ltV0inW18pm6I0m/8b011yOJ8DZb1o="},
    {"email": "rachelle.mallari06@gmail.com", "role": "student", "first_name": "Rachelle", "last_name": "Mallari", "year_level": "1", "password_hash": "pbkdf2_sha256$870000$PLVDPQmwrRTcWUuWSWJ2R6$WFbaUtcgnPngqHYceH1S2jYxaYJJD5RxnpDLqnYhR9M="},
    {"email": "giancarlo.bueno.2006@gmail.com", "role": "student", "first_name": "Gian Carlo", "last_name": "Bueno", "year_level": "1", "password_hash": "pbkdf2_sha256$870000$ENiymlPIhyv1nTwTJdiLs0$x72mjFw6NcYK6mpthGq9FJXZ/bA4EohmPRQudx3sgH4="},
    {"email": "patricia.lim4@gmail.com", "role": "student", "first_name": "Patricia", "last_name": "Lim", "year_level": "1", "password_hash": "pbkdf2_sha256$870000$Hi9foyMXNBe1Lt0x4qn4wq$4aPc3HX+q3rHA9dVqf9UEo4h91f4x3SB4H27FbGGVHY="},
    {"email": "ivan.manzano@gmail.com", "role": "student", "first_name": "Ivan", "last_name": "Manzano", "year_level": "2", "password_hash": "pbkdf2_sha256$870000$ksCiBDg1T5uulDPlVkUF06$xWYtSfe7wsw40YjdCYnwsTyGo8DhFhsZdiLwCIn/saI="},
    {"email": "jasmine.tan04@gmail.com", "role": "student", "first_name": "Jasmine", "last_name": "Tan", "year_level": "2", "password_hash": "pbkdf2_sha256$870000$uXb4IbHrlkqm0dIqMNdyHo$H51AWUQqKEFwQtXAgMRM+VvtoSN8CZqqKEHQuJxObus="},
    {"email": "arvin.castro.2006@gmail.com", "role": "student", "first_name": "Arvin", "last_name": "Castro", "year_level": "2", "password_hash": "pbkdf2_sha256$870000$ixGOApNDG6Z9msGQbuWwMq$k5XYS84hIbkimQVttm4gG1rE7FfMamnmZO/P4Wog5Sg="},
    {"email": "clarisse.domingo7@gmail.com", "role": "student", "first_name": "Clarisse", "last_name": "Domingo", "year_level": "2", "password_hash": "pbkdf2_sha256$870000$LO0HDzsjNf6wGkvCz0lz3s$f7bvz2w/A+Co96tEIspUzZxNldl/A93Ay8Lm0l8I12g="},
    {"email": "noel.serrano@gmail.com", "role": "student", "first_name": "Noel", "last_name": "Serrano", "year_level": "2", "password_hash": "pbkdf2_sha256$870000$6jVPjmrzazVpcln5eBWPFL$I7kZ0s3U3DZIvn+cdSHdPtI7VkTESa3AGU8SGYoxnRQ="},
    {"email": "danica.perez02@gmail.com", "role": "student", "first_name": "Danica", "last_name": "Perez", "year_level": "2", "password_hash": "pbkdf2_sha256$870000$ZeeBPhzMoagOJoCLdk8qX4$3HTH+1NsZqzG4VBWBpOIJHN8eA3S1iN38PJyRT0G2QU="},
    {"email": "rafael.belen.2006@gmail.com", "role": "student", "first_name": "Rafael", "last_name": "Belen", "year_level": "2", "password_hash": "pbkdf2_sha256$870000$PaoWnFJZLPFt3Mhtg2EPtV$KbWi+JnkVrfnUyfg5+HCigAmTN48HM+qJ9oT6kA65lg="},
    {"email": "joanna.vergara1@gmail.com", "role": "student", "first_name": "Joanna", "last_name": "Vergara", "year_level": "2", "password_hash": "pbkdf2_sha256$870000$sdYppZyRLrc0XVprxJS2G2$hR2gVJODbk1ZdczOF7f5HAEBrryhof4z8mqWeDRGlYM="},
    {"email": "emmanuel.quinto@gmail.com", "role": "student", "first_name": "Emmanuel", "last_name": "Quinto", "year_level": "3", "password_hash": "pbkdf2_sha256$870000$GjR4HRf4nyEDR0SN9byP51$tuq4H0Rr4i+fbb+74qOyBA/cyvxvKoFwZVCnWO6P6Ig="},
    {"email": "ysabel.hernandez30@gmail.com", "role": "student", "first_name": "Ysabel", "last_name": "Hernandez", "year_level": "3", "password_hash": "pbkdf2_sha256$870000$3LkgPjlJMiMAQf2rmglmPJ$0d5sQVYoFK6KpfEX4KMpHOsOxhOKwvA1qCGjPTHy5wg="},
    {"email": "kevin.lacsamana.2006@gmail.com", "role": "student", "first_name": "Kevin", "last_name": "Lacsamana", "year_level": "3", "password_hash": "pbkdf2_sha256$870000$SIgjpVxR0wEpesUv8HsBxO$UMQ+CqLE8F+7xrvrxVZ5x26HLvAFKE7eYoiaXoJ1xVs="},
    {"email": "apriljoy.montero4@gmail.com", "role": "student", "first_name": "April Joy", "last_name": "Montero", "year_level": "3", "password_hash": "pbkdf2_sha256$870000$Of1bJ0XSZUzdFKtz3y8OcD$uccgzF2tP8m45RKkedyFW3UQwfBRbd5U+EYuAnwK+wA="},
    {"email": "cedric.bacani@gmail.com", "role": "student", "first_name": "Cedric", "last_name": "Bacani", "year_level": "3", "password_hash": "pbkdf2_sha256$870000$XmpqeOs9FrqbePiG7qlEm3$L5Va2cmDDNIz3RBDo4dK5UNQ+JpKyCf6ydrTfKV7Udw="},
    {"email": "aira.saldivar28@gmail.com", "role": "student", "first_name": "Aira", "last_name": "Saldivar", "year_level": "3", "password_hash": "pbkdf2_sha256$870000$1kxDGiFtYwffQCWZoQuh59$fHqgenwnsDznrkeEhqGXkT8Xdg6eWXsufdCaEnmdejg="},
    {"email": "miguel.roxas.2006@gmail.com", "role": "student", "first_name": "Miguel", "last_name": "Roxas", "year_level": "3", "password_hash": "pbkdf2_sha256$870000$XlIZPqNDpts3K7JK2g16YF$RnWSFC5PQpCinpLff1UbPnR4bvG+dlbOwzxVyTvNwIw="},
    {"email": "charmaine.agustin7@gmail.com", "role": "student", "first_name": "Charmaine", "last_name": "Agustin", "year_level": "4", "password_hash": "pbkdf2_sha256$870000$483uJRM01co44PWVAQD8Hr$KlcbL98yLHzyK5j+z8wzVchLp6xqsMsKpnnb7tcAJg8="},
    {"email": "jayson.delmundo@gmail.com", "role": "student", "first_name": "Jayson", "last_name": "Del Mundo", "year_level": "4", "password_hash": "pbkdf2_sha256$870000$X40ucrrfVEggAz8Jm37DDG$hSWoqqD4xMbTb6R6gr0O+2xhu3RPnX8OzRUkL2Z6hQM="},
    {"email": "precious.marquez26@gmail.com", "role": "student", "first_name": "Precious", "last_name": "Marquez", "year_level": "4", "password_hash": "pbkdf2_sha256$870000$Mi0zHaPW78hLSkzqTIepx7$crTEAj1413GDLPoCVfo4WN0N1YDg/cXVvA+wUpqZtSE="},
    {"email": "aldrin.gatdula.2006@gmail.com", "role": "student", "first_name": "Aldrin", "last_name": "Gatdula", "year_level": "4", "password_hash": "pbkdf2_sha256$870000$XhYMzsJRNinkqvvP0IZHnN$SVfJma3NCugLIe/nLYhBPIosh99LHRQCkOSgrhhu+sE="},
    {"email": "louise.cortez1@gmail.com", "role": "student", "first_name": "Louise", "last_name": "Cortez", "year_level": "4", "password_hash": "pbkdf2_sha256$870000$ShpaRhkQkjwEs82P3QKIAy$iYSxailv7S+G1rrA23aqs9Cquwvi1LwPg6XfqCyB9ns="},
    {"email": "zyrus.maglaque@gmail.com", "role": "student", "first_name": "Zyrus", "last_name": "Maglaque", "year_level": "4", "password_hash": "pbkdf2_sha256$870000$YbkmDzveb9UqtBlZBrQLAp$RWWY3J0mQpsIRBxTkbBmvI69EKdWM/IJMpHXRJjLagw="},
    {"email": "kimberly.arellano24@gmail.com", "role": "student", "first_name": "Kimberly", "last_name": "Arellano", "year_level": "4", "password_hash": "pbkdf2_sha256$870000$ipFgStnnM5TqQ6wWPpTzYt$jS3ZJvGjFLoCcOxym1zBHxLk0loTtBN1mDxFaKYDiWc="},
]


def seed_accounts(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    UserProfile = apps.get_model("signtext", "UserProfile")
    UserLearningState = apps.get_model("signtext", "UserLearningState")

    for account in ACCOUNTS:
        email = account["email"]
        user = User.objects.filter(username__iexact=email).first() or User.objects.filter(email__iexact=email).first()
        if user is None:
            user = User(username=email, email=email, first_name=account["first_name"], last_name=account["last_name"])
        user.password = account["password_hash"]
        user.is_active = True
        user.save()

        profile = UserProfile.objects.filter(user=user).first()
        if profile is None:
            profile = UserProfile(
                user=user,
                full_name=f"{user.first_name} {user.last_name}".strip(),
                first_name=user.first_name,
                last_name=user.last_name,
            )
        profile.role = account["role"]
        profile.active = 0
        profile.year_level = account["year_level"]
        profile.save()

        UserLearningState.objects.get_or_create(user=user)


class Migration(migrations.Migration):
    dependencies = [
        ("signtext", "0038_seed_more_accounts"),
    ]

    operations = [
        migrations.RunPython(seed_accounts, migrations.RunPython.noop),
    ]
