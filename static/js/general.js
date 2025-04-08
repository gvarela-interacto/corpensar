function logout(){
    $.ajax({
        url: "includes/_userlogin/logout.php",
        type: "POST",
        contentType: false,
        processData: false,
        dataType: "json",
            success: function(respuesta) {
            if (respuesta.success === true) {          
                localStorage.removeItem("logged");
                localStorage.removeItem("uid");
                localStorage.removeItem("nombres");
                localStorage.removeItem("apellidos");
                localStorage.removeItem("correoelectronico");
                localStorage.removeItem("whatsapp");
                localStorage.removeItem("rol");
                location.href="login.php";       
            }
        },
        error: function(jqXHR, textStatus, errorThrown) {
            Swal.fire({
                icon: "error",
                title: "Oops...",
                text: "Error el ejecutar la petición"
            });
        }
    });
};
