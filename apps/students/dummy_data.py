from __future__ import annotations

FIRST_NAMES = [
	"Ali",
	"Sara",
	"Hassan",
	"Nora",
	"Omar",
	"Lina",
	"Yousef",
	"Maya",
	"Khaled",
	"Dina",
]

LAST_NAMES = [
	"Ahmed",
	"Mahmoud",
	"Ibrahim",
	"Farouk",
	"Saleh",
	"Nasser",
	"Adel",
	"Tarek",
]

BATCH_IDS = ["b1", "b2", "b3", "b4"]


def build_students_seed(total: int = 220) -> list[dict]:
	students: list[dict] = []
	tuition_fee = 12000

	for index in range(total):
		i = index + 1
		payment_status = "not_paid" if i % 6 == 0 else "partial" if i % 4 == 0 else "paid"
		amount_paid = tuition_fee if payment_status == "paid" else 7000 if payment_status == "partial" else 0
		employment_status = "no" if i % 3 == 0 or i % 8 == 0 else "yes"

		students.append(
			{
				"id": f"s{i}",
				"name": f"{FIRST_NAMES[index % len(FIRST_NAMES)]} {LAST_NAMES[(index * 3) % len(LAST_NAMES)]}",
				"phone": f"09{str(10000000 + i)[-8:]}",
				"batchId": BATCH_IDS[index % len(BATCH_IDS)],
				"paymentStatus": payment_status,
				"tuitionFee": tuition_fee,
				"amountPaid": amount_paid,
				"grade": None if i % 9 == 0 else 55 + ((i * 7) % 45),
				"employmentStatus": employment_status,
			}
		)

	return students


STUDENTS_DUMMY_DATA = build_students_seed()
