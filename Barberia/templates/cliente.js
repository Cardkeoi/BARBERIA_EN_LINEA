// Función para obtener los servicios disponibles y mostrarlos en el select
function obtenerServicios() {
    fetch('/obtener_servicios') // Verifica que esté usando '/obtener_servicios'
        .then(response => response.json())
        .then(data => {
            if (Array.isArray(data)) { // Verifica que data sea un array
                const servicioSelect = document.getElementById("servicioSelect");
                servicioSelect.innerHTML = ''; // Limpiar el select
                data.forEach(servicio => {
                    const option = document.createElement("option");
                    option.value = servicio.id_servicio;
                    option.textContent = `${servicio.nombre_servicio} - $${servicio.precio}`;
                    servicioSelect.appendChild(option);
                });
            } else {
                console.error("Formato inesperado:", data);
            }
        })
        .catch(error => console.error('Error al obtener los servicios:', error));
}

// Llamar a la función cuando se cargue la página
document.addEventListener('DOMContentLoaded', obtenerServicios);

async function cargarCitas() {
    try {
        const response = await fetch('/tus_citas');
        const citas = await response.json();

        console.log("Citas cargadas:", citas); // Agrega esto para depurar

        if (!response.ok) {
            console.error(citas.message);
            return;
        }

        const citasTableBody = document.getElementById("tusCitasTable").querySelector("tbody");
        citasTableBody.innerHTML = '';

        citas.forEach(cita => {
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${cita.fecha_cita}</td>
                <td>${cita.servicio}</td>
                <td>${cita.estado}</td>
            `;
            citasTableBody.appendChild(row);
        });
    } catch (error) {
        console.error("Error al cargar las citas:", error);
    }
}

function editarCita(idCita) {
    // Aquí puedes abrir un modal o formulario para editar la cita
    const nuevaFecha = prompt("Introduce la nueva fecha para la cita:");
    if (nuevaFecha) {
        fetch('/editar_cita', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ id_cita: idCita, nueva_fecha: nuevaFecha }),
        }).then(response => {
            if (response.ok) {
                alert("Cita actualizada");
                location.reload(); // Refrescar para mostrar cambios
            } else {
                alert("Error al actualizar la cita");
            }
        });
    }
}

function cancelarCita(idCita) {
    if (confirm("¿Estás seguro de que deseas cancelar esta cita?")) {
        fetch('/cancelar_cita', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ id_cita: idCita }),
        }).then(response => {
            if (response.ok) {
                alert("Cita cancelada");
                location.reload(); // Refrescar para mostrar cambios
            } else {
                alert("Error al cancelar la cita");
            }
        });
    }
}

document.getElementById('hacerCitaForm').addEventListener('submit', function (e) {
    e.preventDefault();

    const servicio = document.getElementById('servicioSelect').value;
    const fecha = document.getElementById('fechaCita').value;
    const hora = document.getElementById('horaCita').value;

    const submitButton = document.getElementById('hacerCitaBtn');
    submitButton.disabled = true; // Deshabilitar botón para evitar duplicados

    // Verificación de horarios y luego hacer la cita
    fetch('/verificar_horario', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ fecha: fecha, hora: hora }),
    })
        .then(response => response.json())
        .then(data => {
            if (data.disponible) {
                // Si el horario está disponible, hacer la cita
                fetch('/hacer_cita', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ servicio: servicio, fecha: fecha, hora: hora }),
                })
                    .then(response => response.json())
                    .then(data => {
                        alert(data.message);
                        submitButton.disabled = false; // Rehabilitar botón después de la respuesta
                    })
                    .catch(error => {
                        console.error('Error al hacer la cita:', error);
                        submitButton.disabled = false; // Rehabilitar botón en caso de error
                    });
            } else {
                alert(data.message); // Mostrar mensaje si el horario está ocupado
                submitButton.disabled = false; // Rehabilitar botón
            }
        })
        .catch(error => {
            console.error('Error al verificar el horario:', error);
            submitButton.disabled = false; // Rehabilitar botón en caso de error
        });
});
document.getElementById('editarPerfilForm').addEventListener('submit', async function (e) {
    e.preventDefault();

    const email = document.getElementById('email').value.trim();
    const newPassword = document.getElementById('newPassword').value.trim();

    if (!email) {
        alert("El email es obligatorio.");
        return;
    }

    try {
        const response = await fetch('/actualizar_cliente', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, newPassword }),
        });

        const data = await response.json();

        if (response.ok) {
            alert(data.message);
            document.getElementById('editarPerfilForm').reset(); // Limpiar el formulario
        } else {
            alert(`Error: ${data.message}`);
        }
    } catch (error) {
        console.error("Error al actualizar el perfil:", error);
        alert("Ocurrió un error al actualizar el perfil.");
    }
});
