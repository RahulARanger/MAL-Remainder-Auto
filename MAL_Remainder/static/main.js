let expires_in = document.querySelector("footer > div:first-of-type").dataset
	.time;

const set_to = (id, value) => {
	document.getElementById(id).textContent = value;
	document.getElementById(id).nextElementSibling.textContent =
		value > 1 ? "s" : "";
};
const get_id = (id) => Number(document.getElementById(id).textContent);

const timer_id = setInterval(count_down, 1000);

(function () {
	let by = 24 * 60 * 60; // 1 day's hour * 1hr's minutes * 1minutes's seconds

	const days = Math.floor(expires_in / by);
	expires_in -= days * by;
	by /= 24;

	const hours = Math.floor(expires_in / by);
	expires_in -= hours * by;
	by /= 60;

	const minutes = Math.floor(expires_in / by);
	expires_in -= minutes * by;
	by /= 60;

	const seconds = expires_in;

	set_to("days", days);
	set_to("hours", hours);
	set_to("minutes", minutes);
	set_to("seconds", seconds);
})();

function count_down(id, value) {
	const seconds = get_id("seconds");
	if (seconds) {
		return set_to("seconds", seconds - 1);
	}

	set_to("seconds", 59);
	const minutes = get_id("minutes");

	if (minutes) {
		return set_to("minutes", minutes - 1);
	}

	set_to("minutes", 59);
	const hours = get_id("hours");

	if (hours) {
		return set_to("hours", hours - 1);
	}

	set_to("hours", 23);

	const days = get_id("days");
	if (days) {
		return set_to("days", days - 1);
	}

	set_to("seconds", 0);
	set_to("minutes", 0);
	set_to("hours", 0);
	set_to("days", 0);

	document
		.querySelector("header > div:first-of-type")
		.classList.add("expired");

	clearInterval(timer_id);
}


document.querySelector(".corner.right").addEventListener("click", (e) =>
	confirm("Close this session ?\nYou will need to open a new session if required") || e.preventDefault()
);



	