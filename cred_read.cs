using System;
using System.Runtime.InteropServices;

/// <summary>
/// 读取 Windows 凭证管理器中保存的通用凭据（git 把 GitHub token 存在这里）。
/// 仅用于本机发布流程，读完即删。
/// </summary>
public class CredReader
{
    [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool CredRead(string target, int type, int flags, out IntPtr credential);

    [DllImport("advapi32.dll")]
    private static extern void CredFree(IntPtr buffer);

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct CREDENTIAL
    {
        public int Flags;
        public int Type;
        public string TargetName;
        public string Comment;
        public long LastWritten;
        public int CredentialBlobSize;
        public IntPtr CredentialBlob;
        public int Persist;
        public int AttributeCount;
        public IntPtr Attributes;
        public string TargetAlias;
        public string UserName;
    }

    public static string Read(string target)
    {
        IntPtr ptr;
        if (!CredRead(target, 1, 0, out ptr))
        {
            return "";
        }
        try
        {
            CREDENTIAL cred = (CREDENTIAL)Marshal.PtrToStructure(ptr, typeof(CREDENTIAL));
            if (cred.CredentialBlobSize <= 0)
            {
                return "";
            }
            return Marshal.PtrToStringUni(cred.CredentialBlob, cred.CredentialBlobSize / 2);
        }
        finally
        {
            CredFree(ptr);
        }
    }

    public static string UserName(string target)
    {
        IntPtr ptr;
        if (!CredRead(target, 1, 0, out ptr))
        {
            return "";
        }
        try
        {
            CREDENTIAL cred = (CREDENTIAL)Marshal.PtrToStructure(ptr, typeof(CREDENTIAL));
            return cred.UserName ?? "";
        }
        finally
        {
            CredFree(ptr);
        }
    }
}
