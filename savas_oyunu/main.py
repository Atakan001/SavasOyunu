import random
from dataclasses import dataclass
from typing import Optional, Tuple, Callable


# ----------------------------
# Veri Modelleri
# ----------------------------


@dataclass
class Weapon:
    name: str
    min_damage: int
    max_damage: int
    hit_chance: float  # 0.0 - 1.0
    crit_chance: float  # 0.0 - 1.0
    crit_multiplier: float  # örn. 1.75

    def roll_damage(self) -> int:
        return random.randint(self.min_damage, self.max_damage)


class Character:
    def __init__(
        self,
        display_name: str,
        max_health: int,
        shield_ratio: float,  # hasar azaltma yüzdesi (0.0 - 0.6 gibi)
        power: int,  # taban güç, hasara eklenir
        accuracy_bonus: float = 0.0,  # isabet bonusu (0.0 - 0.2)
        block_bonus: float = 0.0,  # ek blok şansı (0.0 - 0.2)
        special_handler: Optional[Callable[["Character", "Character", int, Weapon], Tuple[int, str]]] = None,
        special_name: str = "",
    ) -> None:
        self.display_name = display_name
        self.max_health = max_health
        self.current_health = max_health
        self.shield_ratio = shield_ratio
        self.power = power
        self.accuracy_bonus = accuracy_bonus
        self.block_bonus = block_bonus
        self.weapon: Optional[Weapon] = None
        self.special_handler = special_handler
        self.special_name = special_name

    def is_alive(self) -> bool:
        return self.current_health > 0

    def choose_weapon(self, weapon: Weapon) -> None:
        self.weapon = weapon

    def attack(self, defender: "Character") -> str:
        if self.weapon is None:
            return f"{self.display_name} silahsız saldırmaya çalıştı ama başaramadı!"

        lines = []

        # Vuruş kontrolü
        hit_probability = max(0.05, min(0.95, self.weapon.hit_chance + self.accuracy_bonus))
        hit_roll = random.random()
        if hit_roll > hit_probability:
            lines.append(f"{self.display_name}, {self.weapon.name} ile ISKALADI! (Şans: {hit_probability:.0%})")
            return "\n".join(lines)

        # Hasar hesaplama
        base_damage = self.weapon.roll_damage() + random.randint(self.power // 3, self.power)

        # Kritik vuruş kontrolü
        crit_roll = random.random()
        did_crit = crit_roll < self.weapon.crit_chance
        if did_crit:
            base_damage = int(base_damage * self.weapon.crit_multiplier)
            lines.append(f"KRİTİK! {self.display_name}, {self.weapon.name} ile yıkıcı bir darbe indirdi!")

        # Özel yetenek (saldırana ait). Ek hasar veya etkiler dönebilir
        if self.special_handler is not None:
            extra_damage, special_text = self.special_handler(self, defender, base_damage, self.weapon)
            if special_text:
                lines.append(special_text)
            base_damage += max(0, extra_damage)

        # Savunma ve blok
        damage_after_block, defense_text = defender.defend(base_damage)
        if defense_text:
            lines.append(defense_text)

        defender.current_health = max(0, defender.current_health - damage_after_block)
        lines.append(
            f"{self.display_name}, {defender.display_name}'a {damage_after_block} hasar verdi. "
            f"({defender.display_name} Can: {defender.current_health}/{defender.max_health})"
        )

        return "\n".join(lines)

    def defend(self, incoming_damage: int) -> Tuple[int, str]:
        # Temel blok mantığı: kalkan oranı kadar hasarı azaltır
        # Ek olarak küçük bir şansla "tam blok" veya "şanslı savunma" etkisi olabilir
        text_parts = []

        # Tam blok şansı (düşük). Block bonusu küçük katkı sağlar
        full_block_chance = max(0.0, min(0.25, 0.05 + self.block_bonus / 2))
        if random.random() < full_block_chance:
            text_parts.append(f"{self.display_name} ustaca BLOKLEDİ! (Tam blok)")
            return 0, " ".join(text_parts)

        # Kısmi blok: kalkan oranı kadar sabit azaltım
        reduced = int(round(incoming_damage * (1.0 - self.shield_ratio)))

        # Şanslı savunma: kalan hasarı yarıya indirme ihtimali
        lucky_block_chance = max(0.0, min(0.30, 0.10 + self.block_bonus))
        if random.random() < lucky_block_chance:
            reduced = max(0, reduced // 2)
            text_parts.append(f"{self.display_name} şanslı bir savunma yaptı (hasar yarıya indi)")

        # Metin
        base_reduction_percent = int(self.shield_ratio * 100)
        text_parts.append(f"Kalkan {base_reduction_percent}% hasarı emdi.")

        return max(0, reduced), " ".join(text_parts)


# ----------------------------
# Karakter Örnekleri ve Özel Yetenekler
# ----------------------------


def savasci_special(attacker: Character, defender: Character, current_damage: int, weapon: Weapon) -> Tuple[int, str]:
    # Berserker: %15 ihtimalle ek bir yarım vuruş (50% hasar)
    if random.random() < 0.15:
        bonus = max(1, current_damage // 2)
        return bonus, f"{attacker.display_name}, Berserker oldu! Ek {bonus} hasar."
    return 0, ""


def okcu_special(attacker: Character, defender: Character, current_damage: int, weapon: Weapon) -> Tuple[int, str]:
    # İsabetli Atış: %20 ihtimalle blok yok sayılır (kalkan etkisiz)
    if random.random() < 0.20:
        # Blok yok saymayı, gelen hasarı blok öncesi maksimuma çekerek simüle edelim:
        # Yani defender.defend çağrısı yine yapılacak ama +50% ek hasar vererek kalkanı aşma hissi yaratalım
        # (defend yine çağrılıyor; ancak bu metin, "kalkanı deldi" mesajını verir)
        bonus = max(1, int(current_damage * 0.5))
        return bonus, f"{attacker.display_name}, KALKANI DELDİ! (+{bonus} hasar)"
    return 0, ""


def buyucu_special(attacker: Character, defender: Character, current_damage: int, weapon: Weapon) -> Tuple[int, str]:
    # Büyü Patlaması: %25 ihtimalle elementsel + sabit hasar (kalkan azaltımından daha az etkilenir gibi düşünülür)
    if random.random() < 0.25:
        bonus = random.randint(6, 14) + attacker.power // 2
        return bonus, f"{attacker.display_name}, BÜYÜ PATLAMASI yaptı! (+{bonus} büyü hasarı)"
    return 0, ""


def create_savasci() -> Character:
    return Character(
        display_name="Savaşçı",
        max_health=120,
        shield_ratio=0.25,  # %25 sabit hasar azaltım
        power=12,
        accuracy_bonus=0.05,
        block_bonus=0.05,
        special_handler=savasci_special,
        special_name="Berserker",
    )


def create_okcu() -> Character:
    return Character(
        display_name="Okçu",
        max_health=95,
        shield_ratio=0.15,
        power=10,
        accuracy_bonus=0.12,
        block_bonus=0.03,
        special_handler=okcu_special,
        special_name="İsabetli Atış",
    )


def create_buyucu() -> Character:
    return Character(
        display_name="Büyücü",
        max_health=85,
        shield_ratio=0.10,
        power=16,
        accuracy_bonus=0.08,
        block_bonus=0.02,
        special_handler=buyucu_special,
        special_name="Büyü Patlaması",
    )


# ----------------------------
# Silah Havuzları
# ----------------------------


WARRIOR_WEAPONS = [
    Weapon(name="Katana", min_damage=10, max_damage=18, hit_chance=0.82, crit_chance=0.22, crit_multiplier=1.8),
    Weapon(name="Şövalye Kılıcı", min_damage=12, max_damage=20, hit_chance=0.78, crit_chance=0.18, crit_multiplier=1.7),
    Weapon(name="Pala", min_damage=15, max_damage=24, hit_chance=0.72, crit_chance=0.15, crit_multiplier=1.6),
]


ARCHER_WEAPONS = [
    Weapon(name="Yay", min_damage=9, max_damage=16, hit_chance=0.85, crit_chance=0.20, crit_multiplier=1.9),
    Weapon(name="Kundaklı Yay", min_damage=13, max_damage=22, hit_chance=0.75, crit_chance=0.25, crit_multiplier=2.0),
]


MAGE_WEAPONS = [
    Weapon(name="Asa", min_damage=8, max_damage=14, hit_chance=0.83, crit_chance=0.18, crit_multiplier=1.7),
    Weapon(name="Tılsımlı Asa", min_damage=12, max_damage=19, hit_chance=0.78, crit_chance=0.22, crit_multiplier=1.85),
]


# ----------------------------
# CLI Yardımcıları
# ----------------------------


def ask_int(prompt: str, valid_range: range) -> int:
    while True:
        raw = input(prompt).strip()
        if not raw.isdigit():
            print("Lütfen bir sayı giriniz.")
            continue
        value = int(raw)
        if value in valid_range:
            return value
        print(f"Lütfen {valid_range.start}-{valid_range.stop - 1} arasında bir değer seçiniz.")


def choose_character_and_weapon(is_player: bool = True) -> Character:
    if is_player:
        print("\nKarakterini seç:")
        print("1) Savaşçı")
        print("2) Okçu")
        print("3) Büyücü")
        choice = ask_int("Seçimin: ", range(1, 4))
    else:
        choice = random.choice([1, 2, 3])

    if choice == 1:
        character = create_savasci()
        weapons = WARRIOR_WEAPONS
    elif choice == 2:
        character = create_okcu()
        weapons = ARCHER_WEAPONS
    else:
        character = create_buyucu()
        weapons = MAGE_WEAPONS

    if is_player:
        print(f"\n{character.display_name} seçildi. Silahını seç:")
        for idx, w in enumerate(weapons, start=1):
            print(
                f"{idx}) {w.name} | Hasar: {w.min_damage}-{w.max_damage} | İsabet: {int(w.hit_chance*100)}% "
                f"| Kritik: {int(w.crit_chance*100)}% x{w.crit_multiplier}"
            )
        w_choice = ask_int("Silah seçimin: ", range(1, len(weapons) + 1))
        weapon = weapons[w_choice - 1]
    else:
        weapon = random.choice(weapons)

    character.choose_weapon(weapon)
    return character


def take_turn(attacker: Character, defender: Character) -> None:
    print("\n--- TUR ---")
    print(attacker.attack(defender))


def battle(player: Character, cpu: Character) -> None:
    print("\nSAVAŞ BAŞLADI!")
    print(
        f"Sen: {player.display_name} - Silah: {player.weapon.name} | Can: {player.current_health} | Kalkan: {int(player.shield_ratio*100)}% | Güç: {player.power}"
    )
    print(
        f"Rakip: {cpu.display_name} - Silah: {cpu.weapon.name} | Can: {cpu.current_health} | Kalkan: {int(cpu.shield_ratio*100)}% | Güç: {cpu.power}"
    )

    # Oyuncu ilk başlasın
    attacker, defender = player, cpu
    turn_count = 1
    while player.current_health > 0 and cpu.current_health > 0:
        print(f"\nTur #{turn_count}")
        take_turn(attacker, defender)
        if not defender.is_alive():
            break
        attacker, defender = defender, attacker
        turn_count += 1

    print("\nSAVAŞ BİTTİ!")
    if player.current_health > 0 and cpu.current_health <= 0:
        print("Tebrikler! Kazandın.")
    elif cpu.current_health > 0 and player.current_health <= 0:
        print("Maalesef kaybettin.")
    else:
        print("Berabere gibi... ilginç!")


def main() -> None:
    random.seed()
    print("Metin Tabanlı Savaş Oyunu (TR)")
    print("--------------------------------")

    while True:
        player = choose_character_and_weapon(is_player=True)
        cpu = choose_character_and_weapon(is_player=False)

        print(
            f"\nRakibin: {cpu.display_name} ({cpu.weapon.name}) hazır. {player.display_name} ({player.weapon.name}) saldırıya geç!"
        )
        input("Devam etmek için Enter'a bas...")
        battle(player, cpu)

        again = input("\nYeniden oyna? (e/h): ").strip().lower()
        if again != "e":
            print("Güle güle!")
            break


if __name__ == "__main__":
    main()


