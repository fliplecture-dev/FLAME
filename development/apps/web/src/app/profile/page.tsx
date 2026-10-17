import { redirect } from "next/navigation";
import { apiRequest,sessionValue } from "@/lib/api/auth-bff";
import { StudentProfileForm } from "@/features/auth/student-profile-form";
export default async function ProfilePage(){const session=await sessionValue();if(!session||!(await apiRequest("me","GET",undefined,session)).ok)redirect("/sign-in?next=%2Fprofile");return <StudentProfileForm />;}
