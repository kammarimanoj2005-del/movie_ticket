import json
import os
import sys
import tempfile
import uuid
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

# -------------------- SETTINGS --------------------

DATA_FILE = Path(__file__).resolve().with_name("bookings.json")

SEAT_ROWS = "ABCDEF"
SEATS_PER_ROW = 8
MAX_TICKETS_PER_BOOKING = 8
GST_RATE = Decimal("0.18")

MOVIES = [
    {
        "id": "M001",
        "name": "The Last Horizon",
        "genre": "Science Fiction",
        "duration": "2h 10m",
        "rating": "U/A",
        "ticket_price": 220,
        "showtimes": ["10:00 AM", "2:00 PM", "7:00 PM"]
    },
    {
        "id": "M002",
        "name": "The Hidden Garden",
        "genre": "Drama",
        "duration": "1h 55m",
        "rating": "U",
        "ticket_price": 180,
        "showtimes": ["11:00 AM", "3:30 PM", "8:15 PM"]
    },
    {
        "id": "M003",
        "name": "Midnight Express",
        "genre": "Action",
        "duration": "2h 05m",
        "rating": "U/A",
        "ticket_price": 250,
        "showtimes": ["9:30 AM", "1:15 PM", "6:30 PM"]
    }
]


class BookingStoreError(Exception):
    """Booking data storage error."""
    pass


# -------------------- COMMON FUNCTIONS --------------------

def line():
    print("=" * 76)


def get_text(prompt):
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("\nInput cancelled.")
        raise


def choose_number(prompt, minimum, maximum):

    while True:

        value = get_text(prompt)

        try:
            number = int(value)

        except ValueError:
            print("Please enter a valid whole number.")
            continue

        if minimum <= number <= maximum:
            return number

        print(f"Please enter a number between {minimum} and {maximum}.")


def ask_yes_no(prompt):

    while True:

        answer = get_text(prompt).lower()

        if answer in ("y", "yes"):
            return True

        elif answer in ("n", "no"):
            return False

        else:
            print("Please enter Y or N.")


# -------------------- MOVIE FUNCTIONS --------------------

def show_movies():

    line()
    print("                    NOW SHOWING")
    line()

    for index, movie in enumerate(MOVIES, 1):

        print(f"{index}. {movie['name']} ({movie['rating']})")
        print(f"   Genre: {movie['genre']}")
        print(f"   Duration: {movie['duration']}")
        print(f"   Ticket Price: Rs. {movie['ticket_price']:.2f}")
        print("   Showtimes: " + ", ".join(movie["showtimes"]))
        print("-" * 76)


def choose_movie():

    show_movies()

    choice = choose_number(
        "Choose a movie: ",
        1,
        len(MOVIES)
    )

    return MOVIES[choice - 1]


# -------------------- SHOWTIME SELECTION --------------------

def choose_showtime(movie):

    print(f"\nAvailable showtimes for {movie['name']}:")

    for index, showtime in enumerate(movie["showtimes"], 1):
        print(f"{index}. {showtime}")

    choice = choose_number(
        "Choose a showtime: ",
        1,
        len(movie["showtimes"])
    )

    return movie["showtimes"][choice - 1]


# -------------------- SEAT BOOKING --------------------

def booked_seats(bookings, movie, showtime):

    return {
        seat
        for booking in bookings
        if booking["status"] == "CONFIRMED"
        and booking["movie_id"] == movie["id"]
        and booking["showtime"] == showtime
        for seat in booking["seats"]
    }


def choose_seats(bookings, movie, showtime):

    booked = booked_seats(bookings, movie, showtime)

    all_seats = {
        f"{row}{number}"
        for row in SEAT_ROWS
        for number in range(1, SEATS_PER_ROW + 1)
    }

    available = all_seats - booked

    line()
    print("                 SEAT MAP (XX = BOOKED)")
    line()

    for row in SEAT_ROWS:

        labels = [
            "XX" if f"{row}{number}" in booked
            else f"{row}{number}"
            for number in range(1, SEATS_PER_ROW + 1)
        ]

        print(f"{row}: " + "  ".join(labels))

    line()

    if not available:
        print("This show is fully booked.")
        return []

    maximum = min(MAX_TICKETS_PER_BOOKING, len(available))

    ticket_count = choose_number(
        f"How many tickets do you want to book? (1-{maximum}): ",
        1,
        maximum
    )

    print(f"Enter exactly {ticket_count} different seats.")
    print("Example: A1,A2")
    print("Enter Q to cancel.")

    while True:

        requested = get_text("Enter your seats: ").upper()

        if requested == "Q":
            return []

        seats = [
            seat.strip()
            for seat in requested.split(",")
        ]

        if not requested or any(not seat for seat in seats):

            print("Please enter valid seat numbers.")

        elif len(seats) != ticket_count:

            print(f"Please select exactly {ticket_count} seats.")

        elif len(set(seats)) != len(seats):

            print("Duplicate seats are not allowed.")

        elif any(seat not in available for seat in seats):

            print("Invalid or already-booked seat. Try again.")

        else:
            return seats


# -------------------- BILL CALCULATION --------------------

def show_payment_summary(name, movie, showtime, seats):

    subtotal = Decimal(movie["ticket_price"]) * len(seats)

    gst = (
        subtotal * GST_RATE
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    total = subtotal + gst

    line()
    print("                    BOOKING SUMMARY")
    line()

    print(f"Customer : {name}")
    print(f"Movie    : {movie['name']}")
    print(f"Showtime : {showtime}")
    print(f"Seats    : {', '.join(seats)}")
    print(f"Tickets  : {len(seats)}")
    print(f"Price    : Rs. {movie['ticket_price']:.2f}")
    print(f"Subtotal : Rs. {subtotal:.2f}")
    print(f"GST 18%  : Rs. {gst:.2f}")
    print(f"Total    : Rs. {total:.2f}")

    line()

    return float(subtotal), float(gst), float(total)


# -------------------- CASH PAYMENT ONLY --------------------

def process_payment(total):

    print("\nAmount due: Rs.", f"{total:.2f}")

    print("Payment method: CASH ONLY")

    print("Please collect the cash from the customer.")

    if ask_yes_no("Has the customer paid the cash amount? (y/n): "):

        print("Cash payment received successfully.")

        return "Cash"

    else:

        print("Cash payment not received.")
        return None


# -------------------- FILE HANDLING --------------------

def load_bookings():

    if not DATA_FILE.exists():
        return []

    try:

        with DATA_FILE.open("r", encoding="utf-8") as file:
            bookings = json.load(file)

    except (OSError, json.JSONDecodeError) as error:

        raise BookingStoreError(
            f"Could not read booking data: {error}"
        ) from error

    required = {
        "booking_id",
        "customer_name",
        "movie_id",
        "movie_name",
        "showtime",
        "seats",
        "subtotal",
        "gst",
        "total",
        "payment_method",
        "booking_time",
        "status"
    }

    if not isinstance(bookings, list) or any(
        not isinstance(b, dict)
        or not required.issubset(b)
        or not isinstance(b["seats"], list)
        or b["status"] not in ("CONFIRMED", "CANCELLED")
        for b in bookings
    ):

        raise BookingStoreError("Invalid booking data format.")

    return bookings


def save_bookings(bookings):

    temporary_path = None

    try:

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=DATA_FILE.parent,
            prefix=".bookings.",
            suffix=".tmp",
            delete=False
        ) as file:

            temporary_path = Path(file.name)

            json.dump(
                bookings,
                file,
                ensure_ascii=False,
                indent=2
            )

            file.write("\n")
            file.flush()
            os.fsync(file.fileno())

        temporary_path.replace(DATA_FILE)

    except OSError as error:

        raise BookingStoreError(
            f"Could not save bookings: {error}"
        ) from error

    finally:

        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


# -------------------- PRINT TICKET --------------------

def print_ticket(booking):

    line()
    print("                    MOVIE TICKET")
    line()

    print(f"Booking ID : {booking['booking_id']}")
    print(f"Customer   : {booking['customer_name']}")
    print(f"Movie      : {booking['movie_name']}")
    print(f"Showtime   : {booking['showtime']}")
    print(f"Seats      : {', '.join(booking['seats'])}")
    print(f"Total Paid : Rs. {booking['total']:.2f}")
    print(f"Payment    : {booking['payment_method']}")
    print(f"Booked At  : {booking['booking_time']}")
    print(f"Status     : {booking['status']}")

    line()


# -------------------- BOOK TICKETS --------------------

def book_tickets(bookings):

    line()
    print("                    BOOK TICKETS")
    line()

    while True:

        name = get_text("Enter customer name: ")

        if name and any(char.isalpha() for char in name):
            break

        print("Please enter a valid customer name.")

    movie = choose_movie()

    showtime = choose_showtime(movie)

    seats = choose_seats(bookings, movie, showtime)

    if not seats:

        print("Booking process stopped. No seats were reserved.")
        return

    subtotal, gst, total = show_payment_summary(
        name,
        movie,
        showtime,
        seats
    )

    if not ask_yes_no("\nProceed to cash payment? (y/n): "):

        print("Booking cancelled. Your seats were not reserved.")
        return

    payment_method = process_payment(total)

    if payment_method is None:

        print("Booking not confirmed because cash was not received.")
        return

    booking = {

        "booking_id": "MOV-" + uuid.uuid4().hex[:8].upper(),

        "customer_name": name,

        "movie_id": movie["id"],

        "movie_name": movie["name"],

        "showtime": showtime,

        "seats": seats,

        "subtotal": subtotal,

        "gst": gst,

        "total": total,

        "payment_method": payment_method,

        "booking_time": datetime.now().strftime(
            "%d-%m-%Y %I:%M %p"
        ),

        "status": "CONFIRMED"
    }

    updated = bookings + [booking]

    save_bookings(updated)

    bookings[:] = updated

    print("\nBooking confirmed successfully!")

    print_ticket(booking)


# -------------------- VIEW BOOKINGS --------------------

def view_bookings(bookings):

    line()
    print("                 ALL CONFIRMED BOOKINGS")
    line()

    confirmed = [
        booking for booking in bookings
        if booking["status"] == "CONFIRMED"
    ]

    if not confirmed:

        print("There are no confirmed bookings yet.")
        return

    for booking in confirmed:

        print(f"Booking ID: {booking['booking_id']}")
        print(f"Customer : {booking['customer_name']}")
        print(f"Movie    : {booking['movie_name']}")
        print(f"Showtime : {booking['showtime']}")
        print(f"Seats    : {', '.join(booking['seats'])}")
        print(f"Total    : Rs. {booking['total']:.2f}")
        print(f"Payment  : {booking['payment_method']}")

        print("-" * 76)


# -------------------- CANCEL BOOKING --------------------

def cancel_booking(bookings):

    booking_id = get_text(
        "Enter the booking ID to cancel: "
    ).upper()

    if not booking_id:

        print("Booking ID cannot be empty.")
        return

    for index, booking in enumerate(bookings):

        if booking["booking_id"] == booking_id:

            if booking["status"] == "CANCELLED":

                print("This booking is already cancelled.")
                return

            print(f"Customer: {booking['customer_name']}")
            print(f"Movie: {booking['movie_name']}")
            print(f"Seats: {', '.join(booking['seats'])}")
            print(f"Total: Rs. {booking['total']:.2f}")

            if ask_yes_no("Are you sure you want to cancel? (y/n): "):

                updated = [
                    dict(item) for item in bookings
                ]

                updated[index]["status"] = "CANCELLED"

                save_bookings(updated)

                bookings[:] = updated

                print("Booking cancelled successfully.")
                print("Seats are available again.")

            else:

                print("Cancellation stopped.")

            return

    print("Booking ID not found.")


# -------------------- MAIN MENU --------------------

def main():

    try:

        bookings = load_bookings()

        while True:

            line()
            print("          WELCOME TO MOVIE TICKET BOOKING SYSTEM")
            line()

            print("1. View movies and showtimes")
            print("2. Book movie tickets")
            print("3. View all confirmed bookings")
            print("4. Cancel a booking")
            print("5. Exit")

            line()

            choice = choose_number(
                "Choose an option (1-5): ",
                1,
                5
            )

            if choice == 1:

                show_movies()

            elif choice == 2:

                book_tickets(bookings)

            elif choice == 3:

                view_bookings(bookings)

            elif choice == 4:

                cancel_booking(bookings)

            elif choice == 5:

                print("\nThank you for using the Movie Ticket Booking System!")

                return 0

    except BookingStoreError as error:

        print(f"Error: {error}", file=sys.stderr)

        return 1

    except (EOFError, KeyboardInterrupt):

        print("\nProgram closed safely.")

        return 0


if __name__ == "__main__":

    raise SystemExit(main())