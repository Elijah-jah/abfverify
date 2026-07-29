document.addEventListener("DOMContentLoaded", function () {

    console.log("Change Password JS Loaded");


    // ==========================
    // SHOW / HIDE PASSWORD
    // ==========================

    const toggleButtons = document.querySelectorAll(".toggle-password");

    toggleButtons.forEach(function(button){

        button.addEventListener("click", function(){

            const input = document.getElementById(
                this.dataset.target
            );

            const icon = this.querySelector("i");


            if(input.type === "password"){

                input.type = "text";

                icon.classList.remove("fa-eye");
                icon.classList.add("fa-eye-slash");

            } else {

                input.type = "password";

                icon.classList.remove("fa-eye-slash");
                icon.classList.add("fa-eye");

            }

        });

    });



    // ==========================
    // CHANGE PASSWORD VALIDATION
    // ==========================


    const form = document.querySelector("#changePasswordForm");


    if(form){

        form.addEventListener("submit", function(e){


            const currentPassword = document.getElementById(
                "currentPassword"
            ).value;


            const newPassword = document.getElementById(
                "newPassword"
            ).value;


            const confirmPassword = document.getElementById(
                "confirmPassword"
            ).value;



            // Empty current password

            if(!currentPassword){

                e.preventDefault();

                showToast(
                    "warning",
                    "Please enter your current password."
                );

                return;

            }



            // Empty new password

            if(!newPassword){

                e.preventDefault();

                showToast(
                    "warning",
                    "Please enter your new password."
                );

                return;

            }



            // New password same as old password

            if(currentPassword === newPassword){

                e.preventDefault();

                showToast(
                    "error",
                    "New password cannot be the same as your current password."
                );

                return;

            }



            // Confirm password mismatch

            if(newPassword !== confirmPassword){

                e.preventDefault();

                showToast(
                    "error",
                    "New passwords do not match."
                );

                return;

            }


            // Everything passed

            showToast(
                "success",
                "Password is being updated..."
            );


        });

    }


});