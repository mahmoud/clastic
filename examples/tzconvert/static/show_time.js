async function showResult(event, form) {
    event.preventDefault();
    const response = await fetch(form.action, {
        method: "POST",
        body: new FormData(form),
    });
    const json = await response.json();
    document.getElementById("src_dt").innerHTML = json["src_dt"]["text"];
    document.getElementById("src_dt").setAttribute("datetime", json["src_dt"]["value"]);
    document.getElementById("src_location").innerHTML = json["src_location"];
    document.getElementById("dst_dt").innerHTML = json["dst_dt"]["text"];
    document.getElementById("dst_dt").setAttribute("datetime", json["dst_dt"]["value"]);
    document.getElementById("dst_location").innerHTML = json["dst_location"];
    document.getElementById("result").showModal();
}
